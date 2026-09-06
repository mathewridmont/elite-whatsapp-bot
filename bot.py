import os,time,random,base64,threading,traceback,re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from database import load_players,save_players,get_player,update_level,get_rank

BASE=os.path.dirname(os.path.abspath(__file__))
SESSION=os.path.join(BASE,"storage","whatsapp_session")
os.makedirs(SESSION,exist_ok=True)
players=load_players(); lock=threading.RLock(); state_lock=threading.RLock()
state={"connected":False,"qr":None,"message":"جاري تشغيل Selenium...","error":None,"last_activity":None}
active={}; last_seen=None

CHALLENGES=[
{"question":"ما الرقم التالي؟\n2 - 6 - 12 - 20 - 30 - ؟","answers":["42"],"points":100},
{"question":"شيء كلما أخذت منه كبر. ما هو؟","answers":["الحفرة","حفرة"],"points":100},
{"question":"ما الشيء الذي يمشي بلا أرجل؟","answers":["الوقت"],"points":150},
{"question":"إذا كان لديك 5 تفاحات وأخذت 2، كم أصبح معك؟","answers":["2"],"points":75}]

def set_state(**kw):
    with state_lock:state.update(kw)
def get_public_state():
    with state_lock:return dict(state)
def norm(s):
    for a,b in {"أ":"ا","إ":"ا","آ":"ا","ى":"ي","ة":"ه","ؤ":"و","ئ":"ي"}.items():s=s.replace(a,b)
    return re.sub(r"\s+"," ",(s or "").strip().lower())
def menu():return """╔════════════════════╗
       🎓 ELITE CLASS
╚════════════════════╝

/start — التسجيل
/profile — ملفك
/challenge — تحدٍ جديد
/rank — المتصدرون
/help — المساعدة

⚠️ كل نقطة لها ثمن."""
def profile(p):return f"""╔════════════════════╗
       👤 PROFILE
╚════════════════════╝
الاسم: {p["name"]}
💰 النقاط: {p["points"]}
⭐ المستوى: {p["level"]}
🎯 محلولة: {p["solved"]}
❌ خاطئة: {p["wrong"]}
🏆 الرتبة: {get_rank(p["points"])}"""
def ranking():
    with lock:top=sorted(players.values(),key=lambda p:int(p.get("points",0)),reverse=True)[:10]
    return "لا يوجد لاعبون بعد." if not top else "╔════════════════════╗\n       🏆 TOP 10\n╚════════════════════╝\n\n"+"".join(f'{i}. {p["name"]} — {p["points"]} نقطة\n' for i,p in enumerate(top,1))

def create_driver():
    print("[BOT] Starting Chromium...",flush=True)
    o=webdriver.ChromeOptions()
    o.binary_location=os.environ.get("CHROME_BIN","/usr/bin/chromium")
    for x in ["--headless=new","--no-sandbox","--disable-dev-shm-usage","--disable-gpu","--window-size=1365,1000","--disable-notifications","--disable-extensions","--no-first-run","--no-default-browser-check"]:
        o.add_argument(x)
    o.add_argument(f"--user-data-dir={SESSION}")
    d=webdriver.Chrome(options=o); d.set_page_load_timeout(90); d.implicitly_wait(1)
    print("[BOT] Chromium started.",flush=True);return d

def visible(d,s):
    try:return [e for e in d.find_elements(By.CSS_SELECTOR,s) if e.is_displayed()]
    except:return []
def find_qr(d):
    for s in ["div[data-ref] canvas","div[data-ref]","canvas","img[alt*='QR']"]:
        for e in visible(d,s):
            try:
                b=e.screenshot_as_png
                if b and len(b)>1000:return base64.b64encode(b).decode()
            except:pass
    return None
def connected(d):
    return any(visible(d,s) for s in ["#side","[data-testid='chat-list']","[aria-label='Chat list']","[aria-label='قائمة الدردشات']"])
def incoming(d):
    for s in ["div.message-in","div[data-testid='msg-container']"]:
        x=visible(d,s)
        if x:return x
    return []
def ident(e):
    try:return e.get_attribute("data-id") or e.text+"|"+e.get_attribute("class")
    except:return None
def send(d,text):
    for s in ["footer div[contenteditable='true'][role='textbox']","footer div[contenteditable='true']","div[contenteditable='true'][role='textbox']"]:
        for e in visible(d,s):
            try:e.click();e.send_keys(text);e.send_keys(Keys.ENTER);return True
            except:pass
    return False

def process(d,e):
    global last_seen
    try:text=e.text.strip();key=ident(e)
    except:return
    if not text or key==last_seen:return
    last_seen=key;set_state(last_activity=time.time())
    pid="current-chat"
    with lock:
        p=get_player(players,pid,"Player"); c=norm(text)
        if c=="/start":save_players(players);send(d,menu());return
        if c in ("/help","مساعدة"):send(d,menu());return
        if c=="/profile":send(d,profile(p));return
        if c=="/rank":send(d,ranking());return
        if c=="/challenge":
            ch=random.choice(CHALLENGES);active[pid]=ch
            send(d,f"""╔════════════════════╗
       ⚔️ CHALLENGE
╚════════════════════╝

{ch["question"]}

━━━━━━━━━━━━━━━━━━━━
🎯 الجائزة: {ch["points"]} نقطة
أرسل إجابتك.""");return
        ch=active.get(pid)
        if ch:
            if any(c==norm(a) for a in ch["answers"]):
                p["points"]+=ch["points"];p["solved"]+=1;update_level(p);active.pop(pid,None);save_players(players)
                send(d,f"🎯 إجابة صحيحة.\n\n+{ch['points']} نقطة\n💰 نقاطك: {p['points']}\n⭐ المستوى: {p['level']}\n🏆 الرتبة: {get_rank(p['points'])}")
            else:
                p["wrong"]+=1;save_players(players);send(d,"❌ إجابة خاطئة.\n\nحاول مرة أخرى.")

def bot_loop():
    global last_seen
    delay=5
    while True:
        d=None
        try:
            set_state(connected=False,qr=None,message="جاري تشغيل Selenium...",error=None)
            d=create_driver();d.get("https://web.whatsapp.com/")
            set_state(message="WhatsApp Web مفتوح، جاري تجهيز شاشة الربط...")
            delay=5
            while True:
                if connected(d):
                    set_state(connected=True,qr=None,message="تم ربط WhatsApp بنجاح",error=None)
                    msgs=incoming(d)
                    if msgs:process(d,msgs[-1])
                else:
                    q=find_qr(d)
                    set_state(connected=False,qr=q,message="امسح QR من صفحة الربط" if q else "جاري البحث عن QR...",error=None)
                time.sleep(2)
        except Exception as e:
            print("[BOT ERROR]",repr(e),flush=True);traceback.print_exc()
            set_state(connected=False,qr=None,message="إعادة تشغيل Selenium...",error=f"{type(e).__name__}: {e}")
            try:
                if d:d.quit()
            except:pass
            time.sleep(delay);delay=min(delay*2,60)

threading.Thread(target=bot_loop,name="whatsapp-selenium",daemon=True).start()
