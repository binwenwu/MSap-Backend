import json
import os
import re
import mimetypes
import threading
import time
import unittest

from qgis.core import *

# import sys
# print(sys.path)
# sys.path.append(r"C:\Program Files\GIS\QGIS\apps\qgis-ltr\python\plugins")

import processing

QgsApplication.setPrefixPath(r"D:\GIS\QGIS", True)
qgs = QgsApplication([], False)
qgs.initQgis()
processing.Processing().initialize()


class TestAlg(unittest.TestCase):
	def test_run_alg(self):
		inlayer = r"C:\Users\admin\Desktop\PyWPS\data\point.shp"
		outlayer = r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT.tif'
		result = processing.run("native:buffer", {'INPUT': inlayer, 'OUTPUT': outlayer})
		# print(result["OUTPUT"])
		# time.sleep(30)
		print(result)

	def test_thread_run_alg(self):

		def native_buffer(i, inp, outp):
			print(f"{i}_start_time", time.time())
			processing.run("gdal:merge", {'INPUT': inp, 'OUTPUT': outp})
			print(f"{i}_end_time", time.time())

		input_layers = [
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_58_05.tif", r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_58_05.tif", r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_58_05.tif", r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_58_05.tif", r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_58_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
			[r"C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_merge\INPUT\srtm_59_05.tif"],
		]

		output_layers = [
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT58_59.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT58_59_1.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT58_59_2.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT58_59_3.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT58.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT59.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT59_1.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT59_2.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT59_3.tif',
			r'C:\Users\admin\Desktop\PyWPS\data\temp\OUTPUT59_4.tif',
		]

		threads = []
		print("全部线程start_time", time.time())
		i = 1
		for in_layer, out_layer in zip(input_layers, output_layers):
			thread = threading.Thread(target=native_buffer, args=(i, in_layer, out_layer), name=str(i))
			threads.append(thread)
			i = i + 1
			thread.start()

		for thread in threads:
			thread.join()
		print("全部线程end_time", time.time())

	def test_help_alg(self):
		# processing.algorithmHelp("native:buffer")
		# 获取算子对象
		alg = QgsApplication.processingRegistry().createAlgorithmById("gdal:extractprojection")

		print(alg.id(), alg.name())

		# 获取算子的输入参数
		input_parameters = alg.parameterDefinitions()

		# 遍历参数并打印默认值
		for param in input_parameters:
			print(type(param).__name__)
			print(param.name(), param.typeName(), sep="-")
			print(param.asPythonString())
			print("description：", param.description())
			try:
				# print(param.name(), param.defaultValue(), param.typeName(), param.dataType(), sep=":")
				# print(param.createFileFilter())
				# all_supported_files_str = re.search(r"All supported files(.*?);;", param.createFileFilter())
				# print(re.findall(r"\*\.(\w+)", all_supported_files_str.group(0)))
				print(param.options())
			except:
				pass
			print("============================================")
		processing.algorithmHelp(alg.id())

		# 获取算法的输出参数定义
		output_parameters = alg.outputDefinitions()
		# 打印输出参数类型
		print("###########################################")
		print("Output Parameters:")
		for param in output_parameters:
			print("description：", param.description())
			print(param.name(), "-", param.typeName(), type(param).__name__)
			try:
				print(param.createFileFilter())
			except:
				pass
			print("============================================")

	def test_mimetype(self):
		print(mimetypes.guess_type('example.j2k'))

	def test_input_param_layerType(self):
		# 激活OTB提供者
		processing.Processing().initialize()
		processing.Processing().activateProvider('otbprovider')

		# 获取所有可用算法
		for alg in qgs.processingRegistry().algorithms():
			print(alg.id())
			for param in alg.parameterDefinitions():
				if param.name() != 'OUTPUT':
					has_layer_type = hasattr(param, 'layerType')
					has_create_file_filter = hasattr(param, 'createFileFilter')
					if has_layer_type != has_create_file_filter:
						print(alg.id())

	def test_alg_input_multi(self):
		output_param_set = set()
		for alg in qgs.processingRegistry().algorithms():
			# for param in alg.parameterDefinitions():
			# 	# QgsProcessingParameterMultipleLayers
			# 	# QgsProcessingOutputMultipleLayers
			# 	if isinstance(param, QgsProcessingParameterColor):
			# 		print(alg.id(), param.name())
			for param in alg.outputDefinitions():
				output_param_set.add(type(param).__name__)
		print(output_param_set)

	def test_default_value_null(self):
		default_value_null = set()
		# 遍历所有的 JSON 文件
		for json_file in os.listdir(r'../json_datas'):
			with open(f'../json_datas/{json_file}', 'r', encoding='utf-8') as f:
				# 读取 JSON 内容
				data = json.load(f)
				alg = QgsApplication.processingRegistry().createAlgorithmById(data.get("Identifier"))
				for param in alg.parameterDefinitions():
					# 查看空值对象有几种
					if not param.defaultValue():
						# # 0、0.0、False
						# if param.defaultValue() == 0:
						#     print(alg.id(), param.name(), param.defaultValue())
						if str(param.defaultValue()) == "NULL":
							print(alg.id())
						try:
							default_value_null.add(param.defaultValue())
						except:
							# print(alg.id(), param.name(), param.defaultValue())
							# print(param.asPythonString())
							default_value_null.update(param.defaultValue())

	def test_param_types(self):
		# 存储匹配结果的集合
		matched_parameters = set()
		# 定义正则表达式
		pattern = re.compile(r'"Parameter type":\s*"([^"]*)"')
		# 遍历所有的 JSON 文件
		for json_file in os.listdir(r'../../backup/data'):
			with open(f'../backup/data/{json_file}', 'r', encoding='utf-8') as f:
				# 读取 JSON 内容
				data = json.load(f)

				# 使用正则表达式匹配 Parameter type 的值
				matches = pattern.findall(json.dumps(data))
				for i in matches:
					if i == '':
						print(data["Identifier"])
				# 将匹配结果添加到集合中
				matched_parameters.update(matches)

		print(matched_parameters)
		print(len(matched_parameters))
		return matched_parameters

	def test_fill_map_rule(self):
		param_types = self.test_param_types()
		with open("../../backup/map_rule.json", "r", encoding="utf8") as f:
			data = json.load(f)
		# for item in data:
		# 	if not data[item]:
		# 		if item in param_types:
		# 			data[item] = {
		# 				"wps_type": "LiteralInput",
		# 				"data_type": "string"
		# 			}
		# with open("map_rule.json", "w+", encoding="utf8") as f:
		# 	json.dump(data, f)
		for item in data:
			if item in param_types:
				param_types.remove(item)
		print(param_types)

	def test_feedback(self):
		processing.run("otb:BandMath", {})
		context = QgsProcessingContext()
		feedback = QgsProcessingFeedback()
		inlayer = r'C:\Users\admin\Desktop\PyWPS\算子实验数据\gdal_aspect\INPUT\ASTGTM2_N05W058_dem.tif'
		result = processing.run(
			"gdal:aspect",
			{'INPUT': inlayer, 'OUTPUT': r'TEMPORARY_OUTPUT'},
			context=context,
			feedback=feedback
		)

		print(feedback.textLog())
