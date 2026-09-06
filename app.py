from flask import Flask, jsonify, render_template
from bot import get_state

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    s = get_state()
    return jsonify({
        "connected": s["connected"],
        "message": s["message"],
        "qr": s["qr"],
        "error": s["error"],
    })


@app.route("/health")
def health():
    return "OK", 200
