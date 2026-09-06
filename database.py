import json, os, tempfile, threading
BASE=os.path.dirname(os.path.abspath(__file__))
FILE=os.path.join(BASE,"storage","data","players.json")
LOCK=threading.RLock()
def ensure():
    os.makedirs(os.path.dirname(FILE),exist_ok=True)
    if not os.path.exists(FILE): write({})
def write(data):
    d=os.path.dirname(FILE); fd,tmp=tempfile.mkstemp(dir=d,prefix=".players-",text=True)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,FILE)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def load_players():
    with LOCK:
        ensure()
        try:
            with open(FILE,encoding="utf-8") as f:return json.load(f)
        except:return {}
def save_players(p):
    with LOCK: ensure(); write(p)
def get_player(players,pid,name):
    p=players.setdefault(pid,{"name":name or "Player","points":0,"level":1,"solved":0,"wrong":0})
    p["name"]=name or p.get("name","Player")
    for k,v in (("points",0),("level",1),("solved",0),("wrong",0)):p.setdefault(k,v)
    return p
def update_level(p):p["level"]=int(p.get("points",0))//100+1
def get_rank(n):
    n=int(n)
    if n>=1500:return "👑 الأسطورة"
    if n>=1000:return "💎 العبقري"
    if n>=700:return "🔥 النخبة"
    if n>=400:return "⚔️ المتقدم"
    if n>=200:return "🎯 المحترف"
    return "🟢 المبتدئ"
