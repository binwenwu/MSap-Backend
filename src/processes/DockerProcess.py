import json
import os
import subprocess
import shutil
import uuid
from datetime import datetime, timedelta
from pywps import Process, LiteralInput, LiteralOutput
from pywps.app.Common import Metadata
from pywps.app.exceptions import ProcessError
import re

class DockerProcess(Process):
    def __init__(self, config_path):
        with open(config_path, 'r') as config_file:
            self.config = json.load(config_file)
        paths = self.config.get('paths', None)
        if paths is None:
            self.host_input_path = ''
            self.host_output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs')
        else:
            if 'host_input_path' in self.config['paths']:
                self.host_input_path = self.config['paths']['host_input_path']
            else:
                self.host_input_path = ''
            if 'host_output_path' in self.config['paths']:
                self.host_output_path = self.config['paths']['host_output_path']
            else:
                self.host_output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs')
        if 'use_docker' in self.config and self.config['use_docker']:
            self.container_external_path = self.config['paths']['container_external_path']
            self.container_internal_path = self.config['paths']['container_internal_path']
        self.status = None
        self.message = None
        self.stdout = ''
        self.service_name = None
        self.file_type = ['feature', 'coverage', 'table', 'file', 'text']
        inputs = []
        for input_def in self.config['inputs']:
            identifier = input_def['identifier']
            title = input_def['title']
            data_type = input_def['data_type']
            if data_type == 'list[int]':
                data_type = 'string'
            elif data_type == 'int':
                data_type = 'integer'
            if data_type in self.file_type:
                data_type = 'string'
                input_def['file_path'] = True
            else:
                input_def['file_path'] = False
            allowed_values = input_def.get('allowed_values', [])
            default = input_def.get('default', None)
            if input_def['data_type'] == 'list[int]':
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
            if data_type == 'list[int]':
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

        super(DockerProcess, self).__init__(
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

    def run_script(self, script_dict, params):
        docker_flag = False
        if 'type' in script_dict and script_dict['type'] == 'docker':
            docker_flag = True
        if script_dict.get('parse_mode', None) is not None and script_dict['parse_mode'] == 'placeholder':
            command = script_dict['script']
            working_directory = script_dict['working_directory']
            parameters = script_dict['parameters']
            handled_parameters = []
            for param in parameters:
                if param.startswith('[') and param.endswith(']'):
                    handled_parameters.append(param[1:-1].split(','))
                elif param.startswith('$'):
                    if param[1:] == 'container_external_path':
                        handled_parameters.append(self.container_external_path)
                    elif param[1:] == 'container_internal_path':
                        handled_parameters.append(self.container_internal_path)
                    elif param[1:] == 'timestamp':
                        if self.service_name is None:
                            # 获取当前时间
                            now = datetime.now()
                            # 生成时间戳字符串，格式为 "YYYYMMDD_HHMMSS"
                            timestamp = now.strftime("%Y%m%d_%H%M%S")
                            self.service_name = timestamp
                            current_time = timestamp
                        else:
                            current_time = self.service_name
                        handled_parameters.append(current_time)
                    else:
                        raise ProcessError(f"Not a valid placeholder: {param}")
                elif param in params:
                    if docker_flag:
                        # If the parameter is an input file, replace the path with the mounted path
                        find_flag = False
                        for input_def in self.config['inputs']:
                            if input_def['identifier'] == param and input_def['file_path']:
                                find_flag = True
                                break
                        for output_def in self.config['outputs']:
                            if output_def['identifier'] == param and output_def['file_path']:
                                find_flag = True
                                break
                        if find_flag:
                            docker_path = os.path.join(self.container_internal_path,
                                                       os.path.basename(params[param]))
                            handled_parameters.append(f"'{docker_path}'")
                            continue
                    handled_parameters.append(str(params[param]))

                else:
                    handled_parameters.append(param)
            command = command.format(*handled_parameters)
        else:  # 列表化参数
            # params 传入参数
            command = script_dict['script'].split()
            working_directory = script_dict['working_directory']
            parameters = script_dict['parameters']
            for param in parameters:
                # Replace placeholders with actual paths
                if param in params:
                    if isinstance(params[param], str):
                        if params[param].startswith('[') and params[param].endswith(']'):
                            command.append(' '.join(params[param][1:-1].split(',')))
                        else:
                            if docker_flag:
                                # If the parameter is an input file, replace the path with the mounted path
                                find_flag = False
                                for input_def in self.config['inputs']:
                                    if input_def['identifier'] == param and input_def['file_path']:
                                        find_flag = True
                                        break
                                for output_def in self.config['outputs']:
                                    if output_def['identifier'] == param and output_def['file_path']:
                                        find_flag = True
                                        break
                                if find_flag:
                                    docker_path = os.path.join(self.container_internal_path,
                                                               os.path.basename(params[param]))
                                    command.append(f'"{docker_path}"')
                                    continue
                            command.append(f'"{params[param]}"')
                    else:
                        command.append(str(params[param]))
                else:
                    command.append(str(param))
            command = ' '.join(command)
        # 使用 subprocess.run 执行完整命令
        process = subprocess.run(command, shell=True, cwd=working_directory, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        print(process.stdout.decode('utf-8'))
        print(process.stderr.decode('utf-8'))
        if process.stdout.decode('utf-8') != '':
            self.stdout = process.stdout.decode('utf-8')
        if not script_dict.get('ignore_errors', False) and process.returncode != 0:
            self.status = 'ERROR'
            if self.message is None:
                self.message = process.stderr.decode('utf-8')
            else:
                self.message += '\n'
                self.message += process.stderr.decode('utf-8')
            return
            # raise ProcessError(
            #     f"Process failed with return code {process.returncode}: {process.stderr.decode('utf-8')}")
        else:
            if docker_flag:
                # Move output files from container to file service path
                for output_def in self.config['outputs']:
                    if output_def['identifier'] in parameters and output_def['file_path']:
                        if output_def.get('next_step_input', False):
                            params[output_def['identifier']] = (
                                os.path.join(self.container_external_path,
                                             os.path.basename(params[output_def['identifier']])
                                             ))
                            continue
                        source = os.path.join(self.container_external_path,
                                              os.path.basename(params[output_def['identifier']]))
                        destination = os.path.join(self.host_output_path,
                                                   os.path.basename(params[output_def['identifier']]))
                        if not os.path.exists(source):
                            raise ProcessError(f"Output file {source} not found")
                        shutil.move(str(source), str(destination))
            if process.stderr.decode('utf-8') is not None:
                if self.message is None:
                    if process.stderr.decode('utf-8') != '':
                        self.message = 'WARNING: ' + process.stderr.decode('utf-8')
                else:
                    self.message += '\nWARNING: ' + process.stderr.decode('utf-8')
            print('success')

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
        # handle input params
        for input_def in self.config['inputs']:
            # If input is a literal, set the value
            if not input_def['file_path']:
                # Set input params to provenance
                request_params['INPUT'][input_def['identifier']] = request.inputs[input_def['identifier']][0].data
                # Copy input params to container_params
                command_params[input_def['identifier']] = request.inputs[input_def['identifier']][0].data
                continue
            # If input is a file
            input_file = request.inputs[input_def['identifier']][0].data
            directory, filename = os.path.split(input_file)
            # 如果目录部分为空，则说明路径仅包含文件名, 则默认为host_input_path，否则为用户指定的路径
            if not directory:
                input_file = os.path.join(self.host_input_path, filename)
            if 'use_docker' in self.config and self.config['use_docker']:
                docker_input_file = os.path.join(self.container_external_path, filename)
                # 如果文件不存在，则抛出异常
                if not os.path.exists(docker_input_file):
                    file_name_not_exist = docker_input_file
                    raise ProcessError(f"Input file {file_name_not_exist} not found")
            else:
                # 如果文件不存在，则抛出异常
                if not os.path.exists(input_file):
                    file_name_not_exist = input_file
                    raise ProcessError(f"Input file {file_name_not_exist} not found")
            # 用户请求参数 -> request_params
            request_params['INPUT'][input_def['identifier']] = input_file
            # 命令所用参数 -> command_params
            command_params[input_def['identifier']] = input_file
            # 如果使用docker，则需要将文件拷贝到容器挂载路径
            if 'use_docker' in self.config and self.config['use_docker']:
                # 容器外部挂载文件路径 -> container_external_file
                container_external_file = os.path.join(self.container_external_path, filename)
                # Copy input file to mounted path
                if not os.path.exists(container_external_file):
                    if not os.path.exists(input_file):
                        raise ProcessError(f"Input file: {input_file} not found")
                    shutil.copy(str(input_file), str(container_external_file))

        # handle output params
        for output_def in self.config['outputs']:
            # 如果输出为文件
            if output_def['file_path']:
                # 生成输出文件名
                output_filename = (self.config['identifier'] + '-'
                                   + output_def['identifier'] + '-' + uuid.uuid4().hex)
                if output_def.get('origin_formats', None) is not None:
                    if not output_def['origin_formats'].startswith('.'):
                        output_filename += '.'
                    origin_output_filename = output_filename + output_def['origin_formats']
                    real_output_filename = output_filename + output_def['formats']
                    # 用户请求参数 -> request_params
                    request_params['OUTPUT'][output_def['identifier']] = os.path.join(self.host_output_path,
                                                                                      real_output_filename)
                    # 命令所用参数 -> container_params
                    command_params[output_def['identifier']] = os.path.join(self.host_output_path, origin_output_filename)
                    continue
                # 如果文件后缀名不以'.'开头，则添加'.'
                if not output_def['formats'].startswith('.'):
                    output_filename += '.'
                output_filename += output_def['formats']
                # 用户请求参数 -> request_params
                request_params['OUTPUT'][output_def['identifier']] = os.path.join(self.host_output_path,
                                                                                  output_filename)
                # 命令所用参数 -> container_params
                command_params[output_def['identifier']] = os.path.join(self.host_output_path, output_filename)
                # 此输出将会作为下一个步骤的输入
                if 'next_step_input' in output_def and output_def['next_step_input']:
                    if 'next_step_input' not in request_params:
                        request_params['next_step_input'] = [output_def['identifier']]
                    else:
                        request_params['next_step_input'].append(output_def['identifier'])
        # Set output parameters
        start_time = datetime.now()
        self.provenance["identifier"] = self.identifier
        self.provenance["params"] = request_params
        self.provenance["start_time"] = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        # Execute the docker process
        self.process(command_params)

        # Set output parameters
        for output_def in self.config['outputs']:
            if output_def['file_path']:
                # 默认返回文件服务对应路径
                response.outputs[output_def['identifier']].data = request_params['OUTPUT'][output_def['identifier']]
            else:
                if 're' in output_def:
                    match = re.search(output_def['re'], self.stdout)
                    if match is not None:
                        request_params['OUTPUT'][output_def['identifier']] = match.group(1)
                        response.outputs[output_def['identifier']].data = match.group(1)
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
                if 'return' in output_def and output_def['return'] is None:
                    continue
                if 'next_step_input' in output_def and output_def['next_step_input']:
                    continue
                output_dict = {}
                output_dict['name'] = output_def['identifier']
                output_dict['data_type'] = output_def['data_type']
                output_dict['value'] = request_params['OUTPUT'][output_def['identifier']]
                self.provenance["result"].append(output_dict)
        response.outputs["provenance"].data = self.provenance
        return response

    def _handler(self, request, response):
        # self.host_output_path = request.inputs['host_output_path'][0].data
        return self.cmd_param_parser(request, response)
