from flask import Flask, jsonify, render_template
from bot import get_public_state
app=Flask(__name__,template_folder="templates")
@app.get("/")
def index(): return render_template("index.html")
@app.get("/api/status")
def status(): return jsonify(get_public_state())
@app.get("/health")
def health(): return "OK",200
