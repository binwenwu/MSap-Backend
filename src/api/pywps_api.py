import json
import os
import uuid
import flask
from concurrent.futures import ThreadPoolExecutor
from dao.LocalStorage import Localstorage
from pywps import Service, configuration
from pywps.response.execute import ExecuteResponse
from pywps.response.capabilities import CapabilitiesResponse

storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'local')
storageKeeper = Localstorage(storage_dir)
from strategy.job_store.JobStoreContext import JobStoreContext
from utils.job_task import run_job
import ast

# from dao.mongoStorage import MongoDB
# from processes.QGISProFactory import QGISProcFactory

# 准备所有文件夹
dir_list = ['logs', 'workdir', 'outputs']

for _dir in dir_list:
    if not os.path.exists(_dir):
        os.mkdir(_dir)
        print(f'{_dir} does not exist! Created it!')

# 算子初始化
# 先不使用qgis算子
# processes = QGISProcFactory().init_algorithms()
from processes.DockerProcess import DockerProcess
from processes.LivyProcess import LivyProcess
# config = '/mnt/storage/pywps/src/processes/config/docker'
config = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'processes', 'config', 'docker')
processes = []
for json_file in os.listdir(config):
    if os.path.isfile(os.path.join(config, json_file)):
        processes.append(DockerProcess(os.path.join(config, json_file)))
# config = '/mnt/storage/pywps/src/processes/config/livy'
config = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'processes', 'config', 'livy')
for json_file in os.listdir(config):
    processes.append(LivyProcess(os.path.join(config, json_file)))


# PyWPS service实例
service = Service(processes, ['pywps.cfg'])
# 读取部署模式
deploy_mode = configuration.get_config_value('deploy', 'mode')
job_store_strategy = JobStoreContext(deploy_mode).job_store_strategy()
# 创建线程池
executor = ThreadPoolExecutor()

# 创建flask蓝图
pywps_blue = flask.Blueprint('pywps', __name__)


@pywps_blue.route('/jobs', methods=['POST'])
def execute():
    flask_request = flask.request
    try:
        data = json.loads(flask_request.data)  # 请求体
    except json.decoder.JSONDecodeError as e:
        return flask.jsonify({"status": "FAILED", "message": f"Invalid JSON: {str(e)}"}), 400
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return flask.jsonify({"status": "FAILED", "message": f"Invalid JSON: {str(e)}"}), 400
    if 'inputs' not in data:
        return flask.jsonify({"status": "FAILED", "message": "Invalid JSON: No inputs provided"}), 400
    for key in data['inputs']:
        if isinstance(data['inputs'][key], list):
            data['inputs'][key] = str(data['inputs'][key])
    # 传递host_output_path到输入inputs中
    if 'host_output_path' in data:
        data['inputs']['host_output_path'] = data['host_output_path']
        del data['host_output_path']
    mode = data.get("mode", None)
    if 'mode' in data:
        del data['mode']
    # 生成/获取jobId
    if 'jobId' in data:
        job_id = data['jobId']
    else:
        job_id = uuid.uuid4().hex
        data['jobId'] = job_id
    if mode == "async":
        job_data = {
            "jobId": job_id,
            'identifier': data['identifier'],
            "status": "RUNNING",
            "result": []
        }
        # 异步执行算子
        future = executor.submit(run_job, job_store_strategy, data, job_id)
        job_store_strategy.save_job_timed(job_id, job_data)
        stored_job_data = job_store_strategy.get_job(job_id)
        # ret = future.result()
        # job_store_strategy.del_job(ret['jobId'])
        return flask.jsonify(stored_job_data)
    else:
        provenance = {}
        # 创建一个新的请求对象，并传递预处理后的数据
        new_request = flask.Request.from_values(
            data=json.dumps(data),
            headers=dict(flask_request.headers),
            method=flask_request.method,
            content_type=flask_request.content_type
        )
        # 调用PyWPS服务
        try:
            wps_resp = service.call(new_request)
            if not isinstance(wps_resp, ExecuteResponse):
                if wps_resp.code == 501 or wps_resp.code == 400:
                    raise wps_resp
            wps_resp = wps_resp.json
            # 解析PyWPS服务的响应
            try:
                for val in wps_resp.get('outputs', []):
                    # 从输出中提取provenance信息
                    if val.get('identifier') == 'provenance':
                        provenance = ast.literal_eval(val['data'])
                        break
                if provenance.get('status', None) is None:
                    if wps_resp['status']['status'].upper() == 'FAILED':
                        provenance['status'] = 'FAILED'
                    else:
                        provenance['status'] = 'UNKNOWN'
                message = wps_resp['status']['message']
                if provenance.get('message', None) is not None:
                    message = provenance['message']
                response = {
                    'jobId': job_id,
                    'identifier': data['identifier'],
                    'status': provenance.get('status', 'FAILED'),
                    'message': message,
                    'result': provenance.get('result', [])
                }
                if provenance.get('completionTime', None) is not None:
                    response['completionTime'] = provenance['completionTime']
                if provenance.get('expirationTime', None) is not None:
                    response['expiration_time'] = provenance['expiration_time']

            except KeyError:
                response = {
                    'jobId': job_id,
                    'identifier': data['identifier'],
                    'status': provenance.get('status', 'FAILED'),
                    'message': wps_resp['status']['message']
                }
            job_store_strategy.save_job_timed(job_id, response)
            provenance["jobId"] = job_id
            # del provenance['url']
            storageKeeper.add_one('provenance', provenance)
            status_code = 200
            if response['status'] == 'FAILED':
                status_code = 400
            elif response['status'] == 'ERROR':
                status_code = 502
            return flask.jsonify(response), status_code
        except Exception as e:
            response = {
                'jobId': job_id,
                'identifier': data['identifier'],
                'status': 'FAILED',
                'message': str(e),
            }
            http_code = e.code if hasattr(e, 'code') else 500
            return flask.jsonify(response), http_code


@pywps_blue.route('/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    job_json = job_store_strategy.get_job(job_id)
    if job_json:
        status_code = 200
        if job_json['status'] == 'FAILED':
            status_code = 400
        elif job_json['status'] == 'ERROR':
            status_code = 502
        return flask.jsonify(job_json), status_code
    else:
        return flask.jsonify({"error": "Job not found"}), 404


@pywps_blue.route('/results/<job_id>', methods=['GET'])
def get_job_results(job_id):
    job_json = job_store_strategy.get_job(job_id)
    if job_json:
        return flask.jsonify(job_json['result'])
    else:
        return flask.jsonify({"error": "Job not found"}), 404


@pywps_blue.route('/processes', methods=['GET'])
def get_capabilities():
    """
    Get the capabilities of the WPS server
    """
    flask_request = flask.request
    try:
        pywps_resp = service.call(flask_request)
        if isinstance(pywps_resp, CapabilitiesResponse):
            pass
        elif not isinstance(pywps_resp, ExecuteResponse):
            if pywps_resp.code == 501 or pywps_resp.code == 400:
                raise pywps_resp
        pywps_resp = pywps_resp.json
    except Exception as e:
        return flask.jsonify({"status": "FAILED", "message": str(e)}), 400

    response = flask.jsonify({
        "service": "WPS",
        "version": "2.0",
        "title": pywps_resp["title"],
        "abstract": pywps_resp["abstract"],
        "keywords": pywps_resp["keywords"],
        "keywords_type": pywps_resp["keywords_type"],
        "provider": pywps_resp["provider"],
        "contents": [{"Title": p["title"], "Abstract": p["abstract"], "Identifier": p["identifier"]} for p in
                     pywps_resp["processes"]]
    })
    return response


@pywps_blue.route('/processes/<path:identifier>', methods=['GET'])
def describe_process(identifier):
    alg = storageKeeper.find_one("algorithms", {"Identifier": identifier})
    if alg and '_id' in alg:
        alg['_id'] = str(alg['_id'])
    return flask.jsonify(alg)
