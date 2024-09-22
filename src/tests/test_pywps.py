import json
import os
import time
import unittest
import zipfile

import requests


class TestPyWPS(unittest.TestCase):
	def test_request(self):
		url = "http://127.0.0.1:5000/jobs"
		payload = {
			"identifier": "gdal:extractprojection",
			"inputs": {
				"INPUT": {
					"type": "reference",
					"href": "http://127.0.0.1:5000/static/data/gdal_extractprojection/INPUT/ASTGTM2_N05W058_dem.tif"
				}
			}
		}
		response = requests.post(url, json=payload)
		print(response.text)

	def test_processes(self):
		# 压缩文件
		# for dir_path, dir_names, filenames in os.walk(r"C:\Users\admin\Desktop\PyWPS\pywps-pyqgis\static\data"):
		# 	for file in filenames:
		# 		if file.endswith(".shp"):
		# 			shp_file_path = os.path.join(dir_path, f'{file.split(".")[0]}.zip')
		# 			print(shp_file_path)
		# 			with zipfile.ZipFile(shp_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
		# 				for file_name in filenames:
		# 					file_path = os.path.join(dir_path, file_name)
		# 					zipf.write(file_path, arcname=os.path.relpath(file_path, dir_path))
		# 			break
		url = "http://127.0.0.1:5000/jobs"
		for dir_path, dir_names, filenames in os.walk(r"C:\Users\admin\Desktop\PyWPS\pywps-pyqgis\static\data"):
			for file in filenames:
				if file.endswith(".zip") or file.endswith(".tif"):
					new_path = os.path.join(dir_path, file).replace("\\", "/")
					_url = new_path.split("static/data/")[1]
					identifier = new_path.split("static/data/")[1].split('/')[0].replace('_', ':')

					payload = {
						"identifier": f"{identifier}",
						"inputs": {
							"INPUT": {
								"type": "reference",
								"href": f"http://127.0.0.1:5000/static/data/{_url}"
							}
						}
					}
					response = requests.post(url, json=payload)
					print(f"\033[91m{identifier}\033[0m")
					print(response.text)

	def test_(self):
		print(os.path.join("aaa", "bbb", "ccc"))
