#!/usr/bin/python

from flask import Flask, render_template, request, jsonify
from kubernetes import client, config
import os

DOMAIN = "kool.karmalabs.local"
app = Flask(__name__)


@app.route("/guitaradd", methods=['POST'])
def guitaradd():
    name = request.form['name']
    brand = request.form['brand']
    print name, brand
    result = {'result': 'success'}
    response = jsonify(result)
    response.status_code = 200
    return response
    # failure = {'result': 'failure', 'reason': "Invalid Data"}
    # response = jsonify(failure)
    # response.status_code = 400
    # return response


@app.route("/form")
def guitarform():
    return render_template("form.html", title="Add Your Guitar")


@app.route("/")
def guitarslist():
    """
    display guitars
    """
    if 'KUBERNETES_PORT' in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    crds = client.CustomObjectsApi()
    guitars = crds.list_cluster_custom_object(DOMAIN, "v1", "guitars")["items"]
    return render_template("index.html", title="Guitars", guitars=guitars)


def run():
    app.run(host="0.0.0.0", port=9000)
    run()

if __name__ == '__main__':
    run()