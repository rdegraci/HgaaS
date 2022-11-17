import asyncio
from quart import Quart, jsonify, request, render_template
import glob
import os
from types import ModuleType
from datetime import datetime
from collections import deque
import psutil
import json
import re
import sys
import stat

from quart_auth import basic_auth_required



if len(sys.argv) == 1:
    print("Usage: python3 server.py <path_to_project>")
    print()
    print("your project should have a hgaas.json file in the root directory, modeled after config.json.template")
    print()
    print("alternative usage: python3 server.py init")
    print()
    print("this will initialize an HgaaS project in your current directory")
    sys.exit(1)

if not os.path.isdir(sys.argv[1]):
    print(f"path give ({sys.argv[1]}) is not a valid directory")
    sys.exit(1)

project_dir = os.path.realpath(sys.argv[1])

if len(sys.argv) > 2 and sys.argv[2] == "init":
    if os.path.isfile(project_dir + '/hgaas.json') or os.path.isfile(project_dir + '/.hgaasignore') or os.path.isfile(project_dir + '/hgaas_runner.sh'):
        print("it looks like this is already an hgaas project (hgaas.json, .hgaasignore, or hgaas_runner.sh exist already)")
        sys.exit(1)

    with open(project_dir + '/hgaas_runner.sh', 'w') as f:
        run_template = '#!/usr/bin/env bash\nfor i in $(seq 1 30); do\n    date\n    sleep 0.5\ndone\n'
        f.write(run_template)
    st = os.stat(project_dir + '/hgaas_runner.sh')
    os.chmod(project_dir + '/hgaas_runner.sh', st.st_mode | stat.S_IEXEC)

    with open(project_dir + '/hgaas.json', 'w') as f:
        cfg_template = '{\n    "cmd": "./hgaas_runner.sh",\n    "port": 8082,\n    "auth_user": "",\n    "auth_password": ""\n}'
        f.write(cfg_template)

    with open(project_dir + '/.hgaasignore', 'w') as f:
        f.write("\n")

    print("created haas.json, .hgaasignore, and hgaas_runner.sh files.")
    print("run 'hgaas .' to start your project!")
    sys.exit(0)

if not os.path.isfile(project_dir + '/hgaas.json'):
    print(f"config file does not exist: {project_dir}/hgaas.json")
    sys.exit(1)



config = json.load(open(project_dir + '/hgaas.json'))
config['project_dir'] = project_dir

ignore_regs = []
print(project_dir + '/.hgaasignore')
if os.path.isfile(project_dir + '/.hgaasignore'):
    ignore_regs = [ project_dir + "/" + t.strip() for t in open(project_dir + '/.hgaasignore').readlines() if t != "\n" ]

print(ignore_regs)

app = Quart(__name__, static_url_path='/', static_folder='public', template_folder="public")


app.config['QUART_AUTH_BASIC_USERNAME'] = config['auth_user']
app.config['QUART_AUTH_BASIC_PASSWORD'] = config['auth_password']


blocklist_regs = [ 
    r"\.hgaasignore$", r".*\.crt$", r".*\.csr$", r".*\.key$", r".*DS_STORE$", r".*\.swp$", r".*\.swo$", 
    r".*\.pyc", r"__pycache__", r"node_modules"
]

file_lock_times = {}

log = deque(maxlen=100)
pid = None
running = True


async def run_proc():
    global config, pid, log, running

    while running:
        a = await asyncio.create_subprocess_shell(config['cmd'] + " 2>&1", stdout=asyncio.subprocess.PIPE, cwd=config['project_dir'])
        pid = a.pid

        # read lines iteratively until the process exits
        while True:
            await asyncio.sleep(0.01)
            log.append((await a.stdout.readline()).decode('ascii').rstrip())
            if a.returncode is not None:
                break

        # then flush the buffer
        line = None
        while line != b'':
            line = await a.stdout.readline()
            log.append(line.decode('ascii').rstrip())

        log.append("==========================================")
        await asyncio.sleep(0.1)

async def kill_proc():
    global pid
    # gotta kill the whole process tree manually
    proc = psutil.Process(pid)
    for p in proc.children(recursive=True):
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    try: 
        proc.kill()
    except psutil.NoSuchProcess:
        pass



async def commit_changes():
    pass




@app.route('/')
@basic_auth_required()
async def index():
    return await render_template('index.html')


@app.route('/files')
@basic_auth_required()
async def files():
    global config
    filenames = glob.glob(config['project_dir'] + '/*')
    filenames += glob.glob(config['project_dir'] + '/**/*')
    showfiles = []
    for t in filenames:
        ignore = False
        if os.path.isdir(t):
            continue
        for reg in ignore_regs:
            if re.match(reg, t):
                ignore = True
                break
        for reg in blocklist_regs:
            if re.match(reg, t):
                ignore = True
                break
        if not ignore:
            showfiles.append(t.replace(project_dir, "."))
    return jsonify({"files": showfiles})


@app.route('/read')
@basic_auth_required()
async def read():
    fname = project_dir + '/' + request.args.get('fname')
    if ".." in fname: return jsonify({"error": "no."})
    with open(fname) as f:
        return jsonify({"fname": fname, "content": f.read()})


@app.post('/save')
@basic_auth_required()
async def save():
    global log
    fname = project_dir + '/' + request.args.get('fname')
    if ".." in fname: return jsonify({"error": "no."})
    j = await request.get_json()
    with open(fname, 'w') as f:
        f.write(j['content'])
    await kill_proc()
    await commit_changes()
    return jsonify({"fname": fname})


@app.route('/new')
@basic_auth_required()
async def new():
    fname = project_dir + '/' + request.args.get('fname')
    if ".." in fname: return jsonify({"error": "no."})
    if os.path.isfile(fname):
        return jsonify({})
        print("makign file", fname)
    with open(fname, 'w') as f:
        f.write("\n\n\ndef register(bot):\n    pass\n\n\n")
    await kill_proc()
    await commit_changes()
    return jsonify({})


@app.route('/rm')
@basic_auth_required()
async def rm():
    fname = project_dir + '/' + request.args.get('fname')
    if ".." in fname: return jsonify({"error": "no."})
    os.remove(fname)
    await kill_proc()
    await commit_changes()
    return jsonify({})


@app.route('/logs')
@basic_auth_required()
async def logs():
    return jsonify({"content": "\n".join(log)})


@app.route('/restart')
@basic_auth_required()
async def restart():
    await kill_proc()
    



def file_is_locked(fname):
    return False
    # TODO: implement
    # return (lock is less than 10 seconds old) 


@app.route('/lock/<fname>')
@basic_auth_required()
async def lock():
    if not file_is_locked(fname):
        file_lock_times[fname] = datetime.now()
    return jsonify({})


@app.route('/lock_status/<fname>')
@basic_auth_required()
async def lock_status():
    return jsonify({"fname": fname, "locked": file_is_locked(fname)})



@app.while_serving
async def close_process_after_shutdown():
    global running
    yield
    running = False
    await kill_proc()



if __name__ == "__main__":
    port = 8082
    if 'port' in config:
        port = config['port']
    if 'PORT' in os.environ:
        port = os.environ['PORT']

    loop = asyncio.get_event_loop()

    if 'ssl_crt' in config and 'ssl_key' in config:
        run_task = app.run(host='0.0.0.0', port=port, ssl_context=(config['ssl_crt'], config['ssl_key']))
    else:
        run_task = app.run_task(host='0.0.0.0', port=port)

    loop.run_until_complete(asyncio.gather(
        run_task, 
        run_proc(),
    ))

