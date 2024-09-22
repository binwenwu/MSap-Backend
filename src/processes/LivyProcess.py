import json
import os
import uuid
from datetime import datetime, timedelta
from pywps import Process, LiteralInput, LiteralOutput
from pywps.app.Common import Metadata
from pywps.app.exceptions import ProcessError
import time
import requests
import shutil
import re
import ast

class LivyProcess(Process):
    def __init__(self, config_path):
        with open(config_path, 'r') as config_file:
            self.config = json.load(config_file)
        paths = self.config.get('paths', None)
        if paths is None:
            self.host_input_path = ''
            self.host_output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs')
            print(self.host_output_path)
        else:
            if 'host_input_path' in self.config['paths']:
                self.host_input_path = self.config['paths']['host_input_path']
            else:
                self.host_input_path = ''
            if 'host_output_path' in self.config['paths']:
                self.host_output_path = self.config['paths']['host_output_path']
            else:
                self.host_output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs')
        self.base_url = self.config['base_url']
        self.status = None
        self.message = None
        self.service_name = None
        self.check_status_url = None
        self.return_value = None
        self.file_type = ['feature', 'coverage', 'table', 'file', 'text', 'directory']
        inputs = []
        list_pattern = re.compile(r'(?i)^list\[(.*?)\]$')
        for input_def in self.config['inputs']:
            identifier = input_def['identifier']
            title = input_def['title']
            data_type = input_def['data_type']
            optional = input_def.get('optional', False)
            default = input_def.get('default', None)
            if identifier == 'jobId':
                default = "null"
            if optional:
                if default is None:
                    default = 'null'
            if list_pattern.match(data_type):
                data_type = 'string'
            elif data_type == 'int':
                data_type = 'integer'
            if data_type in self.file_type:
                data_type = 'string'
                input_def['file_path'] = True
            else:
                input_def['file_path'] = False
            allowed_values = input_def.get('allowed_values', [])
            if list_pattern.match(data_type) and default is not None:
                default = str(default)
            inputs.append(LiteralInput(identifier, title, data_type=data_type,
                                       allowed_values=allowed_values, default=default))
        inputs.append(LiteralInput('host_output_path', 'host_output_path params',
                                   data_type='string', default=self.host_output_path))
        outputs = []
        for output_def in self.config['outputs']:
            identifier = output_def['identifier']
            title = output_def['title']
            data_type = output_def['data_type']
            if list_pattern.match(data_type):
                data_type = 'string'
            elif data_type == 'int':
                data_type = 'integer'
            if data_type in self.file_type:
                data_type = 'string'
                output_def['file_path'] = True
            else:
                output_def['file_path'] = False
            outputs.append(LiteralOutput(identifier, title, data_type=data_type))
        outputs.append(LiteralOutput('provenance', 'provenance', data_type='string'))

        super(LivyProcess, self).__init__(
            handler=self._handler,
            identifier=self.config['identifier'],
            title=self.config['title'],
            abstract=self.config['abstract'],
            metadata=[Metadata(self.config['title'])],
            version=self.config['version'],
            inputs=inputs,
            outputs=outputs
        )
        self.provenance = {}

    @staticmethod
    def send_request(method, url, **kwargs):
        max_retries = 5
        backoff_factor = 1
        status_forcelist = [500, 502, 503, 504]
        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                if e.response is not None and e.response.status_code in status_forcelist:
                    wait_time = backoff_factor * (2 ** attempt)
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise requests.exceptions.HTTPError(f"{e}")

    def find_idle_session(self):
        url = self.base_url + '/sessions'
        try:
            response = self.send_request('GET', url, timeout=10)
            sessions = response.json()
            for session in sessions['sessions']:
                if session['state'] == 'idle':
                    return session['id']
            return None
        except requests.exceptions.HTTPError as e:
            self.status = 'FAILED'
            raise ProcessError(f"Livy HTTP Error: {e}")

    def fetch_livy_process(self):
        # 获取livy任务的状态
        response = self.send_request('GET', self.check_status_url)
        if response.status_code != 200:
            raise requests.exceptions.HTTPError('Cannot fetch livy process status, please try again later.')
        return response.json()

    def sync_fetch_livy_process(self):
        while True:
            data = self.fetch_livy_process()
            if data['state'] == 'available':
                if data.get('output', None) is not None:
                    if data['output'].get('status', None) is not None:
                        if data['output']['status'] == 'error':
                            self.status = 'ERROR'
                            self.message = f"{data['output']['ename']}:{data['output']['evalue']}"
                            traceback_data = data['output'].get('traceback', None)
                            if traceback_data is not None:
                                if isinstance(traceback_data, list):
                                    count = 0
                                    for traceback in traceback_data:
                                        self.message += '\n' + traceback
                                        count += 1
                                        if count > 5:
                                            break
                                    # self.message += '\n' + traceback_data[0]
                            break
                        elif data['output']['status'] == 'ok':
                            self.status = 'SUCCESS'
                            return_value = data['output']['data']['text/plain']
                            if isinstance(return_value, str):
                                match = re.search(r'res(\d+): com\.alibaba\.fastjson\.JSONObject = ({.*})',
                                                  return_value)
                                if match is not None:
                                    self.return_value = json.loads(match.group(2))
                                else:
                                    match = re.search(r'res(\d+): Int = (\d+)', return_value)
                                    if match is not None:
                                        self.return_value = match.group(2)
                                pass
                            break
                        else:
                            self.status = 'ERROR'
                            self.message = 'Unknown status: ' + data['output']['status']
                            break
                self.status = 'SUCCESS'
                break
            elif data['state'] == 'running' or data['state'] == 'waiting':
                time.sleep(2)
            elif data['state'] == 'cancelling':
                self.status = 'ERROR'
                self.message = 'Livy process is cancelling'
                raise ProcessError('Livy process is cancelling')
            elif data['state'] == 'cancelled':
                self.status = 'ERROR'
                self.message = 'Livy process is cancelled'
                raise ProcessError('Livy process is cancelled')
            elif data['state'] == 'error':
                self.status = 'ERROR'
                self.message = f"{data['output']['ename']}:{data['output']['evalue']}"
                raise ProcessError('Livy process is error')
            else:
                self.status = 'ERROR'
                raise ProcessError('Livy process is unknown state')

    def run_script(self, script_dict, params):
        parameters = script_dict['parameters']
        params_map = {}
        for param in parameters:
            # Replace placeholders with actual paths
            if param in params:
                if isinstance(params[param], str):
                    if params[param].startswith('[') and params[param].endswith(']'):
                        flag = False
                        for input_def in self.config['inputs']:
                            if input_def['identifier'] == param and input_def['data_type'] == 'List[coverage]':
                                value = params[param].replace('"', r'\"')
                                value = f'"{value}"'
                                # value = f"\"\"\"{params[param]}\"\"\""
                                params_map[param] = value
                                flag = True
                                break
                        for output_def in self.config['outputs']:
                            if output_def['identifier'] == param and output_def['data_type'] == 'List[coverage]':
                                value = params[param].replace('"', r'\"')
                                value = f'"{value}"'
                                # value = f"\"\"\"{params[param]}\"\"\""
                                params_map[param] = value
                                flag = True
                                break
                        if flag:
                            continue
                        value = ' '.join(params[param][1:-1].split(','))
                        params_map[param] = value
                    else:
                        params_map[param] = f"\"{params[param]}\""
                else:
                    params_map[param] = params[param]
        for key, value in params_map.items():
            if value is None:
                params_map[key] = 'null'
            elif isinstance(value, bool):
                params_map[key] = str(value).lower()
        code_str = script_dict['code']
        formatted_code_str = code_str.format(**params_map)
        headers = {"Content-Type": "application/json"}
        data = {"code": formatted_code_str}
        idle_session_id = self.find_idle_session()
        if idle_session_id is None:
            self.status = 'FAILED'
            raise ProcessError("No idle session found, please try again later.")
        url = self.base_url + f'/sessions/{idle_session_id}/statements'
        try:
            response = self.send_request('POST', url, headers=headers, json=data, timeout=10)
            if response.status_code != 201:
                raise requests.exceptions.HTTPError(f"{response.status_code}")
            task_id = response.json()['id']
            self.check_status_url = self.base_url + f'/sessions/{idle_session_id}/statements/{task_id}'
            self.sync_fetch_livy_process()
            print('success')
        except requests.exceptions.HTTPError as e:
            self.status = 'FAILED'
            raise ProcessError(f"Livy HTTP Error: {e}")

    def process(self, params):
        if isinstance(self.config['execution'], list):
            for script_dict in self.config['execution']:
                self.run_script(script_dict, params)
        else:
            script_dict = self.config['execution']
            self.run_script(script_dict, params)
        if self.status is None:
            self.status = 'SUCCESS'

    def cmd_param_parser(self, request, response):
        request_params = {'INPUT': {}, 'OUTPUT': {}}
        command_params = {}
        job_id = None
        # handle input params
        for input_def in self.config['inputs']:
            # If input is a literal, set the value
            if not input_def['file_path']:
                if input_def['data_type'] == 'List[coverage]':
                    try:
                        if isinstance(request.inputs[input_def['identifier']][0].data, str):
                            list_data = ast.literal_eval(request.inputs[input_def['identifier']][0].data)
                        else:
                            list_data = request.inputs[input_def['identifier']][0].data
                    except json.JSONDecodeError:
                        raise ProcessError(f"Not a valid JSON string: {input_def['identifier']}.")
                    for file in list_data:
                        if not os.path.exists(file):
                            raise ProcessError(f"Input file {file} not found")
                    # Set input params to provenance
                    format_str = json.dumps(list_data)
                    request_params['INPUT'][input_def['identifier']] = format_str
                    command_params[input_def['identifier']] = format_str
                    continue
                # Set input params to provenance
                request_params['INPUT'][input_def['identifier']] = request.inputs[input_def['identifier']][0].data
                # Copy input params to container_params
                command_params[input_def['identifier']] = request.inputs[input_def['identifier']][0].data
                if command_params[input_def['identifier']] == 'null':
                    command_params[input_def['identifier']] = None
                if input_def['identifier'] == 'jobId':
                    # 将字节串转换为字符串
                    data_str = request.http_request.data.decode('utf-8')
                    # 将字符串解析为字典
                    data_dict = json.loads(data_str)
                    # 提取 jobId
                    job_id = data_dict["jobId"]
                    # 设置 jobId
                    command_params[input_def['identifier']] = job_id
                continue
            # If input is a file
            input_file = request.inputs[input_def['identifier']][0].data
            directory, filename = os.path.split(input_file)
            # 如果目录部分为空，则说明路径仅包含文件名, 则默认为host_input_path，否则为用户指定的路径
            if not directory:
                input_file = os.path.join(self.host_input_path, filename)
            if not os.path.exists(input_file):
                raise ProcessError(f"Input file {input_file} not found")
            # 用户请求参数 -> request_params
            request_params['INPUT'][input_def['identifier']] = input_file
            # 命令所用参数 -> command_params
            command_params[input_def['identifier']] = input_file

        # handle output params
        for output_def in self.config['outputs']:
            # 如果输出为文件
            if output_def['file_path']:
                # 生成输出文件名
                output_filename = (self.config['identifier'] + '-'
                                   + output_def['identifier'] + '-' + uuid.uuid4().hex)
                if output_def['data_type'] != 'directory':  # 如果输出不为目录
                    # 如果文件后缀名不以'.'开头，则添加'.'
                    if not output_def['formats'].startswith('.'):
                        output_filename += '.'
                    output_filename += output_def['formats']
                # else:
                #     os.makedirs(os.path.join(self.host_output_path, output_filename), exist_ok=True)
                if output_def['data_type'] == 'directory' and not output_def.get('mkdir', True):
                    # 用户请求参数 -> request_params
                    request_params['OUTPUT'][output_def['identifier']] = os.path.join(self.host_output_path, job_id)
                    # 命令所用参数 -> command_params
                    command_params[output_def['identifier']] = self.host_output_path
                else:
                    # 用户请求参数 -> request_params
                    request_params['OUTPUT'][output_def['identifier']] = os.path.join(self.host_output_path,
                                                                                      output_filename)
                    # 命令所用参数 -> command_params
                    command_params[output_def['identifier']] = os.path.join(self.host_output_path, output_filename)
                # 此输出将会作为下一个步骤的输入
                if 'next_step_input' in output_def and output_def['next_step_input']:
                    if 'next_step_input' not in request_params:
                        request_params['next_step_input'] = [output_def['identifier']]
                    else:
                        request_params['next_step_input'].append(output_def['identifier'])
            else:
                if "return" not in output_def:
                    request_params['OUTPUT'][output_def['identifier']] = None
                else:
                    request_params['OUTPUT'][output_def['identifier']] = output_def["return"]

        # Set output parameters
        start_time = datetime.now()
        self.provenance["identifier"] = self.identifier
        self.provenance["params"] = request_params
        self.provenance["start_time"] = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Execute the process
        self.process(command_params)

        # Set output parameters
        for output_def in self.config['outputs']:
            if output_def['file_path']:
                # 默认返回文件服务对应路径
                response.outputs[output_def['identifier']].data = request_params['OUTPUT'][output_def['identifier']]
        estimated_completion = datetime.now()
        expiration_time = estimated_completion + timedelta(days=1)
        self.provenance["completionTime"] = estimated_completion.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        self.provenance["expiration_time"] = expiration_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        self.provenance["run_time"] = (estimated_completion - start_time).total_seconds()
        self.provenance["status"] = f"{self.status}"
        self.provenance['message'] = self.message
        self.provenance["result"] = []
        if self.status == 'SUCCESS':
            for output_def in self.config['outputs']:
                output_dict = {}
                output_dict['name'] = output_def['identifier']
                output_dict['data_type'] = output_def['data_type']
                if output_def['file_path']:
                    output_path = request_params['OUTPUT'][output_def['identifier']]
                    file_path, ext = os.path.splitext(output_path)
                    if not os.path.exists(output_path):
                        raise ProcessError(f"Output path {output_path} not found")
                    if output_def['data_type'] == 'directory' and os.path.isdir(file_path) and 'formats' in output_def:
                        if not os.listdir(file_path):
                            raise ProcessError(f"Output path {output_path} is empty")
                        # 输出文件为目录，则压缩目录
                        shutil.make_archive(file_path, output_def['formats'], root_dir=os.path.dirname(file_path),
                                            base_dir=os.path.basename(file_path))
                        output_dict['value'] = request_params['OUTPUT'][output_def['identifier']] + '.' + output_def['formats']
                    else:
                        output_dict['value'] = request_params['OUTPUT'][output_def['identifier']]
                else:

                    if isinstance(output_def["return"], str) and '$jobId' in output_def["return"] and job_id is not None:
                        output_def["return"] = output_def["return"].replace('$jobId', job_id)
                    elif isinstance(output_def["return"], str) and f"${output_def['identifier']}" in output_def["return"]:
                        if self.return_value is not None and output_def['identifier'] in self.return_value:
                            output_def["return"] = self.return_value[output_def['identifier']]
                        else:
                            output_def["return"] = None
                    request_params['OUTPUT'][output_def['identifier']] = output_def["return"]
                    output_dict['value'] = request_params['OUTPUT'][output_def['identifier']]
                self.provenance["result"].append(output_dict)
        response.outputs["provenance"].data = self.provenance
        return response

    def _handler(self, request, response):
        self.host_output_path = request.inputs['host_output_path'][0].data
        return self.cmd_param_parser(request, response)
