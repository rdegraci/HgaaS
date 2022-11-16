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

from quart_auth import basic_auth_required

app = Quart(__name__, static_url_path='/', static_folder='public', template_folder="public")

config = json.load(open('./config.json'))
if os.path.isfile(config['project_dir'] + '/.hgaasignore'):
	ignore_regs = [ t.strip() for t in open(config['project_dir'] + '/.hgaasignore').readlines() ]
else:
	ignore_regs = []

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
        a = await asyncio.create_subprocess_shell(config['cmd'], stdout=asyncio.subprocess.PIPE)
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
	loop.run_until_complete(asyncio.gather(
		app.run_task(host='0.0.0.0', port=port), 
		run_proc(),
	))
    # app.run(host='0.0.0.0', port=8081, ssl_context=('bodygen_re.crt', 'bodygen_re.key'))

