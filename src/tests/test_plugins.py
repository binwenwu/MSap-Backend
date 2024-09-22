import unittest


class TestPlugins(unittest.TestCase):
	def test_otb(self):
		from qgis.core import QgsApplication
		import processing
		from otbprovider.OtbAlgorithmProvider import OtbAlgorithmProvider

		from processing.core.ProcessingConfig import ProcessingConfig, Setting

		qgs = QgsApplication([], False)
		otb_setting = Setting(
			ProcessingConfig.tr('General'),
			'OTB_FOLDER',
			ProcessingConfig.tr('OTB installation folder'), True)
		otb_setting.value = r"D:\Desktop\OTB"
		ProcessingConfig().addSetting(otb_setting)

		otbprovider = OtbAlgorithmProvider()
		otbprovider.loadAlgorithms()
		qgs.processingRegistry().addProvider(otbprovider)

		print(QgsApplication.prefixPath())

		processing.Processing().initialize()
		# 遍历所有注册的提供商
		for provider in qgs.processingRegistry().providers():
			# 打印提供商的名称和其提供的算子数量
			print(provider.name(), 'provides', len(provider.algorithms()), 'algorithms')
