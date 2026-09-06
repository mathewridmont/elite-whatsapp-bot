from flask import Flask,render_template,request,redirect,url_for,session,jsonify
from functools import wraps
import os,urllib.parse
from config import SECRET,ADMIN_USER,ADMIN_PASSWORD
app=Flask(__name__,template_folder="templates");app.secret_key=SECRET

def auth(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get("admin"): return redirect(url_for("login",next=request.path))
        return f(*a,**k)
    return w

@app.get("/health")
def health(): return "OK",200

@app.route("/login",methods=["GET","POST"])
def login():
    error=None
    if request.method=="POST":
        if request.form.get("username")==ADMIN_USER and request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True
            return redirect(request.args.get("next") or "/")
        error="بيانات الدخول غير صحيحة"
    return render_template("login.html",error=error)

@app.get("/logout")
def logout():
    session.clear();return redirect("/login")

@app.get("/")
@auth
def index():
    return render_template("index.html")

@app.get("/browser")
@auth
def browser():
    # noVNC's web client is served by the container on port 6080.
    # Render's single public service port cannot expose a second port directly,
    # so this page embeds a websocket URL relative to the public host.
    return render_template("browser.html")

@app.get("/api/status")
@auth
def status():
    return jsonify(ok=True,message="Chrome و noVNC يعملان داخل Render")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
