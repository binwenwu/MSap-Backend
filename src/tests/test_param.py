import mimetypes
import re
import unittest
import processing
from qgis.core import *
from context.qgis import get_qgis

from src.algorithm_init.process_alg_wps import get_algorithm_help, process_algorithm_info

# 初始化QGIS算子，保证能够正常调用
qgs = get_qgis()


class TestAlg(unittest.TestCase):

	def test_get_params(self):
		import requests
		import re

		headers = {
			"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
		}
		url = "https://docs.qgis.org/3.34/en/docs/user_manual/processing/parameters.html"
		response = requests.get(url, headers=headers)

		# print(response.text)
		params = re.findall('<span class="pre">(.*?)</span>', response.text)
		params = [i for i in params if "alg." not in i]
		print(params)
		print(len(params))

	def test_param_type(self):
		# for json_file in os.listdir(r'../algorithm_init/json_datas'):
		# 	with open(f'../algorithm_init/json_datas/{json_file}', 'r', encoding='utf-8') as f:
		# 		# 读取 JSON 内容
		# 		data = json.load(f)
		# 		for param in data["Inputs"]:
		# 			try:
		# 				print(param["Parameter type"])
		# 			except:
		# 				print(data["Identifier"], "####################")
		for alg in qgs.processingRegistry().algorithms():
			alg_help = get_algorithm_help(alg)
			data = process_algorithm_info(alg_help)
			for param in data["Inputs"]:
				if param["Parameter type"] == "QgsProcessingParameterMapLayer":
					print(data["Identifier"])

	def test_param_types(self):
		createFileFilter_param_type_set = set()
		param_type_set = set()
		input_param_dict = dict()
		for alg in qgs.processingRegistry().algorithms():
			for param in alg.parameterDefinitions():
				if param.type() == "maptheme":
					print(alg.id(), param.name())

				# 保存算子支持的文件格式
				try:
					file_type_str = param.createFileFilter()
					all_supported_files_match = re.search(r"All supported files(.*?);;", file_type_str)
					if all_supported_files_match:
						extensions = re.findall(r"\*(.\w+)", all_supported_files_match.group(0))
					else:
						extensions = re.findall(r"\*(.\w+)", file_type_str)

					unique_mime_types = set()  # 集合去重
					mimetypes.add_type("x-world/x-vrt", ".vrt")
					for ext in extensions:
						mime_type, _ = mimetypes.guess_type(f'example{ext}')
						if mime_type:
							unique_mime_types.add(mime_type)
					if unique_mime_types:
						createFileFilter_param_type_set.add(param.type())
						input_param_dict["wps_type"] = "ComplexInput"
						input_param_dict["supported_formats"] = list(unique_mime_types)
					else:
						param_type_set.add(param.type())
						input_param_dict["wps_type"] = "LiteralInput"
						input_param_dict["data_type"] = "string"
				except:
					param_type_set.add(param.type())
					input_param_dict["wps_type"] = "LiteralInput"
					input_param_dict["data_type"] = "string"

		print(param_type_set)
		print(createFileFilter_param_type_set)
		# print({key: {'wps_type': 'LiteralData', 'data_type': ''} for key in param_type_set})
		# print({key: {'wps_type': 'ComplexData', 'data_type': ''} for key in createFileFilter_param_type_set})
		processing.algorithmHelp("native:rasterize")


