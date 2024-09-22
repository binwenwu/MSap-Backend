import json
import flask
from dao.LocalStorage import Localstorage

# from dao.mongoStorage import MongoDB
storageKeeper = Localstorage(
    "/Users/tankenqi/Desktop/大学/ypgroup/OGE竞赛/code/MSap-Backend/local"
)
# 创建flask蓝图
provenance_blue = flask.Blueprint("provenance", __name__)


@provenance_blue.route("/provenances/job_id/<job_id>", methods=["GET"])
def get_job_provenances(job_id):
    provenance = storageKeeper.find_one("porvenance", {"jobId": job_id})
    if not provenance:
        return flask.jsonify({"error": "Job not found"}), 404
    return flask.jsonify(provenance)


@provenance_blue.route("/provenances/identifier/<path:identifier>", methods=["GET"])
def get_identifier_provenances(identifier):
    provenance = storageKeeper.find_many("provenance", {"Identifier": identifier})
    if not provenance:
        return flask.jsonify({"count": 0, "data": []}), 200
    return flask.jsonify({"count": len(provenance), "data": provenance})
