import json
import time
import requests
import threading
from urllib3 import PoolManager, Retry
from urllib3.exceptions import HTTPError

def run_job(job_store_strategy, data, job_id):
	"""
	运行job任务
	Args:
		job_store_strategy: 存储job任务的策略
		data: 请求体
		job_id: job-id
	"""
	try:
		job_data = requests.post('http://127.0.0.1:5000/jobs', json=data, timeout=36000).json()
	except:
		job_data = {
			"jobId": job_id,
			"status": "FAILED",
			"result": {},
			"timestamp": time.time()
		}

	# 将任务状态和结果存储起来
	job_store_strategy.save_job_timed(job_id, job_data)
	return job_data


def fetch_livy_process(job_data):
	check_status_url = job_data.get('url', None)
	if check_status_url is None:
		return None
	# 获取livy任务的状态
	http = PoolManager(num_pools=1)
	retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
	response = http.request('GET', check_status_url, retries=retries)
	if response.status != 200:
		raise HTTPError('http status code is not 200')
	data = json.loads(response.data.decode('utf-8'))
	state = data.get('state')
	if state == 'waiting' or state == 'running':  # 如果任务还在运行中
		job_data['timestamp'] = time.time()
	elif state == 'available':
		output = data.get('output')
		status = output.get('status')
		if status == 'ok':
			job_data['status'] = 'SUCCESS'
			job_data['result'] = output
			job_data['timestamp'] = time.time()
		else:
			job_data['status'] = 'ERROR'
			job_data['message'] = output['ename'] + ':' + output['evalue']
			job_data['timestamp'] = time.time()
	elif state == 'error':
		output = data.get('output')
		job_data['status'] = 'ERROR'
		job_data['message'] = output['ename'] + ':' + output['evalue']
		job_data['timestamp'] = time.time()
	else:
		job_data['status'] = 'FAILED'
		job_data['message'] = 'Unknown state'
	return data


def cleanup_thread_func(job_store_strategy):
	while True:
		job_store_strategy.cleanup_expired_jobs()
		time.sleep(3600)  # 每小时检查一次


def start_cleanup_thread(job_store_strategy):
	cleanup_thread = threading.Thread(target=cleanup_thread_func, args=(job_store_strategy,), daemon=True)
	cleanup_thread.start()
