from qgis.core import QgsApplication
from qgis.server import *
app = QgsApplication([], False)

# 创建server实例
server = QgsServer()

# 通过指定完整的URL和可选的主体来创建请求
request = QgsBufferServerRequest('http://localhost:8081/?MAP=D:\\qgis\\projects\\world.qgs&SERVICE=WMS&REQUEST=GetCapabilities')

# 创建响应对象
response = QgsBufferServerResponse()

# 处理请求
server.handleRequest(request, response)

print(response.headers())
print(response.body().data().decode('utf8'))

app.exitQgis()
