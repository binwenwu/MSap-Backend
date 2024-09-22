# import pymongo
#
# client = pymongo.MongoClient(host='localhost', port=27017)
# db = client.mydb
#
# print(list(db.character.find()))

from dao.mongoStorage import MongoDB

mongo = MongoDB()
dic = {
    "Title": "Tessellate",
    "Abstract": "This algorithm tessellates a polygon geometry layer, dividing the geometries into triangular components.The output layer consists of multipolygon geometries for each input feature, with each multipolygon consisting of multiple triangle component polygons.",
    "Identifier": "3d:tessellate",
    "Inputs": [
        {
            "Title": "INPUT",
            "Abstract": "Input layer",
            "Identifier": "INPUT",
            "Parameter type": "QgsProcessingParameterFeatureSource",
            "Accepted data types": [
                {
                    "str": "layer ID"
                },
                {
                    "str": "layer name"
                },
                {
                    "str": "layer source"
                },
                "QgsProcessingFeatureSourceDefinition",
                "QgsProperty",
                "QgsVectorLayer"
            ],
            "default_value": "None",
            "min_occurs": 1
        }
    ],
    "Outputs": [
        {
            "Title": "OUTPUT",
            "Abstract": "Tessellated",
            "Parameter type": "QgsProcessingOutputVectorLayer"
        }
    ]
}
dic1 = {"Title": "Assign projection", "Abstract": "", "Identifier": "gdal:assignprojection", "Input": [[{"Title": "INPUT"}, {"Abstract": "Input layer"}, {"Identifier": "INPUT"}, {"Parameter type": "QgsProcessingParameterRasterLayer"}, {"Accepted data types": [{"str": "layer ID"}, {"str": "layer name"}, {"str": "layer source"}, "QgsProperty", "QgsRasterLayer"]}], [{"Title": "CRS"}, {"Abstract": "Desired CRS"}, {"Identifier": "CRS"}, {"Parameter type": "QgsProcessingParameterCrs"}, {"Accepted data types": [{"str": "'ProjectCrs'"}, {"str": "CRS auth ID (e.g. 'EPSG:3111')"}, {"str": "CRS PROJ4 (e.g. 'PROJ4:\u2026')"}, {"str": "CRS WKT (e.g. 'WKT:\u2026')"}, {"str": "layer ID. CRS of layer is used."}, {"str": "layer name. CRS of layer is used."}, {"str": "layer source. CRS of layer is used."}, "QgsCoordinateReferenceSystem", {"QgsMapLayer": "CRS of layer is used"}, {"QgsProcessingFeatureSourceDefinition": "CRS of source is used"}, "QgsProperty"]}]], "Outputs": [{"Title": "OUTPUT"}, {"Abstract": "Layer with projection"}, {"Parameter type": "QgsProcessingOutputRasterLayer"}]}
mongo.add_many("algorithms", [dic, dic1, dic])
# print(mongo.find_one('alg', {"Identifier": "3d:tessellate"}).get("_id"))
