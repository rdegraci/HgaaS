import asyncio
from quart import Quart, jsonify, request
import glob
import os
from types import ModuleType
from datetime import datetime
from collections import deque

app = Quart(__name__, static_url_path='/public', static_folder='public', template_folder="templates")


modules_dir = "./modules/JewD/modules"

file_lock_times = {}

logfname = "process.log"
log = deque(maxlen=10)
proc = None
cmd = '/mnt/c/Users/danie/OneDrive/Documents/HgaaS/a.sh'

log.append('asdf')
log.append('qwer')
log.append('yuiop')
log.append('zxcv')

async def monitor_process():
	global proc, log
	while True:
		if proc is None:
			print("no process running")
			await asyncio.sleep(1)
		else:
			data = await proc.stdout.readline()
			line = data.decode('ascii').rstrip()
			print("process>>>> " + line)
			log.append(line)

async def start_process():
	global proc
	proc = await asyncio.create_subprocess_shell(
		cmd,
		stdout=asyncio.subprocess.PIPE,
	)

async def restart_process():
	await proc.kill()
	prod = None
	start_process()

async def commit_changes():
	pass

# start_process()

@app.route('/files')
async def files():
	filenames = glob.glob(modules_dir + '/*')
	filenames = [ t for t in filenames if not os.path.isdir(t) ]
	return jsonify({"files": filenames})

@app.route('/read')
async def read():
	fname = request.args.get('fname')
	if ".." in fname: return jsonify({"error": "no."})
	with open(fname) as f:
		return jsonify({"fname": fname, "content": f.read()})

@app.route('/save')
async def save(fname):
	fname = request.args.get('fname')
	if ".." in fname: return jsonify({"error": "no."})
	with open(fname) as f:
		f.write(request.json['content'])
	restart_process()
	commit_changes()
	return jsonify({"fname": fname})

@app.route('/new')
async def new(fname):
	fname = request.args.get('fname')
	if ".." in fname: return jsonify({"error": "no."})
	with open(fname) as f:
		f.write("\n\n\ndef register(bot):\n    pass\n\n\n")
	restart_process()
	commit_changes()
	return jsonify({})

@app.route('/rm')
async def rm(fname):
	fname = request.args.get('fname')
	if ".." in fname: return jsonify({"error": "no."})
	os.remove(fname)
	restart_process()
	commit_changes()
	return jsonify({})

@app.route('/logs')
async def logs():
	return jsonify({"content": "\n".join(log)})

@app.route('/restart')
async def restart():
	if proc is None:
		await start_process()
	else:
		await restart_process()
	return ""




def file_is_locked(fname):
	return False
	# TODO: implement
	# return (lock is less than 10 seconds old) 

@app.route('/lock/<fname>')
async def lock():
	if not file_is_locked(fname):
		file_lock_times[fname] = datetime.now()
	return jsonify({})

@app.route('/lock_status/<fname>')
async def lock_status():
	return jsonify({"fname": fname, "locked": file_is_locked(fname)})


# TODO: process manager: start, stop, restart, record logs




if __name__ == "__main__":
	loop = asyncio.get_event_loop()
	loop.run_until_complete(asyncio.gather(
		app.run_task(host='0.0.0.0', port=8081), 
		monitor_process()
	))
    # app.run(host='0.0.0.0', port=8081, ssl_context=('bodygen_re.crt', 'bodygen_re.key'))

