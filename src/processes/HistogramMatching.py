from pywps import Process, ComplexInput, ComplexOutput, LiteralInput, LiteralOutput, Format
from pywps.app.Common import Metadata
import os
import subprocess
import shutil
import uuid
from datetime import datetime, timedelta


class HistogramMatching(Process):
    def __init__(self):
        inputs = [
            LiteralInput('GRID', 'Grid File Path',
                         data_type='string'),
            LiteralInput('REFERENCE', 'Reference File Path',
                         data_type='string'),
            LiteralInput('METHOD', 'Method',
                         data_type='integer',
                         allowed_values=[1, 2, 3])
        ]
        outputs = [
            ComplexOutput('MATCHED', 'Matched Output',
                          supported_formats=[Format('image/tiff')]),
            LiteralOutput('provenance', 'provenance', data_type='string')
        ]

        super(HistogramMatching, self).__init__(
            handler=self._handler,
            identifier='HistogramMatching',
            title='Histogram Matching Process',
            abstract='Matches the histogram of a grid to a reference grid',
            metadata=[Metadata('Histogram Matching')],
            version='1.0.0',
            inputs=inputs,
            outputs=outputs
        )
        self.provenance = {}

    @staticmethod
    def process_histogram_matching(grid_file, reference_file, method, matched_file):
        # Construct command
        command = [
            'python', 'HistogramMatching.py',
            '--GRID', grid_file,
            '--REFERENCE', reference_file,
            '--METHOD', str(method),
            '--MATCHED', matched_file
        ]
        # Change working directory
        working_directory = '/mnt/storage/pythonAlgorithm'
        # Execute command
        process = subprocess.run(command, cwd=working_directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # # 打印标准输出和标准错误
        # print("STDOUT:", process.stdout.decode('utf-8'))
        # print("STDERR:", process.stderr.decode('utf-8'))
        # Check for errors
        if process.returncode != 0:
            raise Exception(f"Process failed with return code {process.returncode}: {process.stderr.decode('utf-8')}")
        else:
            print('success')

    def _handler(self, request, response):
        # 获取输入参数
        grid_file = request.inputs['GRID'][0].data
        reference_file = request.inputs['REFERENCE'][0].data
        method = request.inputs['METHOD'][0].data
        # 设置输出文件
        output_filename = uuid.uuid4().hex + '.tif'
        matched_file = os.path.join('/tmp/saga', "result1.tif")
        start_time = datetime.now()
        self.provenance["name"] = self.identifier
        self.provenance["params"] = {
            "INPUT": {
                "GRID": grid_file,
                "REFERENCE": reference_file,
                "METHOD": method
            },
            "OUTPUT": {
                "MATCHED": matched_file
            }
        }

        self.provenance["start_time"] = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        # 执行处理
        self.process_histogram_matching(grid_file, reference_file, method, matched_file)
        # 设置输出参数
        output_file = os.path.join('/mnt/storage/SAGA/sagaData', "result1.tif")
        response.outputs['MATCHED'].file = output_file
        shutil.copy(output_file, os.path.join('/mnt/storage/pywps/outputs', output_filename))

        # 设置处理过程信息
        estimated_completion = datetime.now()
        expiration_time = estimated_completion + timedelta(days=1)
        self.provenance["estimated_completion"] = estimated_completion.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        self.provenance["expiration_time"] = expiration_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        self.provenance["run_time"] = (estimated_completion - start_time).total_seconds()
        self.provenance["status"] = f"{self.identifier} successfully completed"
        self.provenance["result"] = {
            "OUTPUT": "http://localhost:5000/outputs/" + output_filename
        }
        response.outputs["provenance"].data = self.provenance
        return response

# from flask import Flask, request, jsonify, Response
# from pywps import Service
#
# app = Flask(__name__)
#
# # 创建PyWPS服务
# processes = [HistogramMatching()]
# service = Service(processes)
#
# @app.route('/wps', methods=['POST'])
# def wps():
#     try:
#         # 使用PyWPS服务处理请求
#         response = service.call(request)
#         print(response.message)
#         return jsonify({'message': str(response.message), 'output': str(response.outputs)}), 200
#     except Exception as e:
#         print(f"An error occurred: {e}")
#         return jsonify({"error": str(e)}), 500
#
# if __name__ == '__main__':
#     app.run(debug=False, host='0.0.0.0', port=5000)
