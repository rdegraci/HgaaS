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

from quart_auth import basic_auth_required



if len(sys.argv) == 1:
    print("Usage: python3 server.py <path_to_project>")
    print()
    print("your project should have a hgaas.json file in the root directory, modeled after config.json.template")
    sys.exit(1)

if not os.path.isdir(sys.argv[1]):
    print(f"path give ({sys.argv[1]}) is not a valid directory")
    sys.exit(1)

if not os.path.isfile(sys.argv[1] + '/hgaas.json'):
    print(f"config file does not exist: {sys.argv[1]}/hgaas.json")
    sys.exit(1)


project_dir = os.path.realpath(sys.argv[1])

config = json.load(open(project_dir + '/hgaas.json'))
config['project_dir'] = project_dir

ignore_regs = []
if os.path.isfile(project_dir + '/.hgaasignore'):
    ignore_regs = [ t.strip() for t in open(project_dir + '/.hgaasignore').readlines() ]


app = Quart(__name__, static_url_path='/', static_folder='public', template_folder="public")


app.config['QUART_AUTH_BASIC_USERNAME'] = config['auth_user']
app.config['QUART_AUTH_BASIC_PASSWORD'] = config['auth_password']


blacklist_regs = [ r".*\.crt", r".*\.key", r".*DS_STORE", r".*\.swp", r".*\.swo" ]

file_lock_times = {}

log = deque(maxlen=100)
pid = None
running = True


async def run_proc():
    global config, pid, log, running

    while running:
        a = await asyncio.create_subprocess_shell(config['cmd'], stdout=asyncio.subprocess.PIPE, cwd=config['project_dir'])
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
        if os.path.isdir(t):
            continue
        for reg in ignore_regs:
            if re.match(reg, t):
                continue
        for reg in blacklist_regs:
            if re.match(reg, t):
                continue
        showfiles.append(t)
    return jsonify({"files": showfiles})


@app.route('/read')
@basic_auth_required()
async def read():
    fname = request.args.get('fname')
    if ".." in fname: return jsonify({"error": "no."})
    with open(fname) as f:
        return jsonify({"fname": fname, "content": f.read()})


@app.post('/save')
@basic_auth_required()
async def save():
    global log
    fname = request.args.get('fname')
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
    fname = request.args.get('fname')
    if ".." in fname: return jsonify({"error": "no."})
    with open(fname) as f:
        f.write("\n\n\ndef register(bot):\n    pass\n\n\n")
    await kill_proc()
    await commit_changes()
    return jsonify({})


@app.route('/rm')
@basic_auth_required()
async def rm():
    fname = request.args.get('fname')
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

