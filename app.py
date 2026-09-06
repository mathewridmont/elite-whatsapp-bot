from flask import Flask,render_template,jsonify,request,redirect,url_for,session
from functools import wraps
from config import ADMIN_USER,ADMIN_PASSWORD,SECRET
from whatsapp import state,request_pairing,reset,start

app=Flask(__name__,template_folder="templates");app.secret_key=SECRET

def auth(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get("admin"):return redirect(url_for("login",next=request.path))
        return f(*a,**k)
    return w

@app.get("/health")
def health():return "OK",200

@app.route("/login",methods=["GET","POST"])
def login():
    err=None
    if request.method=="POST":
        if request.form.get("username")==ADMIN_USER and request.form.get("password")==ADMIN_PASSWORD:
            session["admin"]=True;return redirect(request.args.get("next") or "/admin")
        err="بيانات الدخول غير صحيحة"
    return render_template("login.html",error=err)

@app.get("/logout")
def logout():session.clear();return redirect("/login")

@app.get("/")
def home():return redirect("/admin")

@app.get("/pair")
def pair():return render_template("pair.html")

@app.post("/api/pair")
def api_pair():
    try:
        request_pairing(request.form.get("phone",""))
        return jsonify(ok=True,message="تم استلام الرقم")
    except Exception as e:return jsonify(ok=False,error=str(e)),400

@app.get("/api/status")
def api_status():return jsonify(state())

@app.post("/admin/restart")
@auth
def admin_restart():reset();return redirect("/admin")

@app.get("/admin")
@auth
def admin():return render_template("admin.html")

start()
