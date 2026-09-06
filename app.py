from flask import Flask,render_template,jsonify,session,redirect,url_for,request
from functools import wraps
from config import ADMIN_USER,ADMIN_PASSWORD,SECRET
from whatsapp import state,reset_session

app=Flask(__name__,template_folder="templates")
app.secret_key=SECRET

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
    err=None
    if request.method=="POST":
        if request.form.get("username")==ADMIN_USER and request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True
            return redirect(request.args.get("next") or "/admin")
        err="بيانات الدخول غير صحيحة"
    return render_template("login.html",error=err)

@app.get("/logout")
def logout(): session.clear(); return redirect("/login")

@app.get("/")
def home(): return redirect("/admin")

@app.get("/qr")
def qr(): return render_template("qr.html")

@app.get("/api/status")
def api_status(): return jsonify(state())

@app.post("/admin/restart-whatsapp")
@auth
def restart():
    reset_session()
    return redirect("/admin")

@app.get("/admin")
@auth
def admin(): return render_template("admin.html")

from whatsapp import start
start()
