import json, os, tempfile, threading
BASE_DIR=os.path.dirname(os.path.abspath(__file__))
DATA_FILE=os.path.join(BASE_DIR,"storage","data","players.json")
LOCK=threading.RLock()
def _ensure():
    os.makedirs(os.path.dirname(DATA_FILE),exist_ok=True)
    if not os.path.exists(DATA_FILE): _write({})
def _write(data):
    d=os.path.dirname(DATA_FILE); fd,tmp=tempfile.mkstemp(dir=d,prefix=".players-",text=True)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,DATA_FILE)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
def load_players():
    with LOCK:
        _ensure()
        try:
            with open(DATA_FILE,encoding="utf-8") as f: return json.load(f)
        except (OSError,json.JSONDecodeError): return {}
def save_players(players):
    with LOCK: _ensure(); _write(players)
def get_player(players,pid,name):
    p=players.setdefault(pid,{"name":name or "Player","points":0,"level":1,"solved":0,"wrong":0})
    p["name"]=name or p.get("name","Player")
    for k,v in (("points",0),("level",1),("solved",0),("wrong",0)): p.setdefault(k,v)
    return p
def update_level(p): p["level"]=int(p.get("points",0))//100+1
def get_rank(points):
    n=int(points)
    if n>=1500:return "👑 الأسطورة"
    if n>=1000:return "💎 العبقري"
    if n>=700:return "🔥 النخبة"
    if n>=400:return "⚔️ المتقدم"
    if n>=200:return "🎯 المحترف"
    return "🟢 المبتدئ"
