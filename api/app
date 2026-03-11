from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "REDNOVA API ONLINE"

@app.route("/investigar")
def investigar():

    target = request.args.get("target")

    result = {
        "target": target,
        "status": "investigation module running"
    }

    return jsonify(result)
