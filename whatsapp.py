import os,re,time,threading,subprocess,traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from config import SESSION,DEBUG
from screenshot_worker import start as start_screens, stop as stop_screens

LOCK=threading.RLock()
S={"connected":False,"ready":False,"message":"بدء Chrome...","error":None,"phone":"","code":"",
   "requested":False,"stage":"boot","url":"","title":"","chrome":"","driver":"","screenshot":"","updated":0}
PHONE="";REQUEST=False;RESTART=False

def setv(**kw):
    with LOCK:S.update(kw);S["updated"]=time.time()
def state():
    with LOCK:return dict(S)
def cmd(c):
    try:return subprocess.check_output(c,stderr=subprocess.STDOUT,text=True,timeout=10).strip()
    except Exception as e:return "unavailable: "+str(e)

def options():
    o=webdriver.ChromeOptions();o.binary_location=os.getenv("CHROME_BIN","/usr/bin/chromium")
    for a in ["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-gpu","--disable-software-rasterizer",
              "--window-size=1365,900","--disable-extensions","--disable-notifications","--no-first-run",
              "--no-default-browser-check","--disable-popup-blocking","--disable-background-networking","--disable-sync",
              "--remote-debugging-port=9222","--remote-allow-origins=*",
              f"--user-data-dir={os.path.join(SESSION,'chrome-profile')}"]:
        o.add_argument(a)
    o.add_argument("--lang=en-US");return o

def make():
    if not os.path.exists("/tmp/.X11-unix/X99"):raise RuntimeError("Xvfb :99 is not ready")
    setv(chrome=cmd(["chromium","--version"]),driver=cmd(["chromedriver","--version"]))
    service=webdriver.ChromeService(executable_path=os.getenv("CHROMEDRIVER_BIN","/usr/bin/chromedriver"),
                                    log_output=os.path.join(DEBUG,"chromedriver.log"))
    service.service_args=["--verbose"]
    d=webdriver.Chrome(service=service,options=options());d.set_page_load_timeout(120);d.implicitly_wait(.5);return d

def body(d):
    try:return d.find_element(By.TAG_NAME,"body").text
    except:return ""

def snap(d):
    try:
        p=os.path.join(DEBUG,"whatsapp.png");d.save_screenshot(p);return "/debug/whatsapp.png?t="+str(int(time.time()))
    except:return ""

def connected(d):
    b=body(d).lower()
    return any(x in b for x in ["chats","archived","communities"]) or any(d.find_elements(By.CSS_SELECTOR,s) for s in ["#side","[data-testid='chat-list']"])

def norm(s):return re.sub(r"\s+"," ",(s or "").strip()).lower()

def visible_elements(d):
    try:
        for e in d.find_elements(By.XPATH,"//*"):
            try:
                if e.is_displayed():yield e
            except:pass
    except:pass

def click_phone_login(d):
    # Search broadly by visible text, aria-label, title and common WhatsApp wording.
    needles=["log in with phone number","login with phone number","link with phone number",
             "log in with a phone number","link with a phone number","phone number"]
    for e in visible_elements(d):
        try:
            vals=[e.text,e.get_attribute("aria-label"),e.get_attribute("title")]
            joined=" | ".join(norm(v) for v in vals if v)
            if any(n in joined for n in needles):
                # Avoid clicking a generic phone input/label if a real button exists.
                tag=e.tag_name.lower()
                role=(e.get_attribute("role") or "").lower()
                if tag in ("button","a") or role=="button" or "link with phone" in joined or "log in with phone" in joined:
                    d.execute_script("arguments[0].click();",e);return True
        except:pass
    return False

def find_phone_input(d):
    selectors=["input[type='tel']","input[inputmode='tel']","input[placeholder*='phone' i]",
               "input[aria-label*='phone' i]","input[name*='phone' i]"]
    for s in selectors:
        try:
            for e in d.find_elements(By.CSS_SELECTOR,s):
                if e.is_displayed():return e
        except:pass
    return None

def click_next(d):
    needles=["next","continue","متابعة","التالي"]
    for e in visible_elements(d):
        try:
            if e.tag_name.lower() not in ("button","a") and (e.get_attribute("role") or "").lower()!="button":continue
            t=norm(e.text)+" "+norm(e.get_attribute("aria-label"))
            if any(n==t or n in t for n in needles):
                d.execute_script("arguments[0].click();",e);return True
        except:pass
    return False

def extract_code(d):
    # Only accept an exact 8-character pairing code, normally shown as 4+4.
    texts=[]
    try:texts.append(body(d))
    except:pass
    for e in visible_elements(d):
        try:
            for v in [e.text,e.get_attribute("aria-label"),e.get_attribute("title"),e.get_attribute("value")]:
                if v:texts.append(v)
        except:pass
    for text in texts:
        for m in re.finditer(r"(?<![A-Z0-9])([A-Z0-9]{4})[\s-]+([A-Z0-9]{4})(?![A-Z0-9])",text.upper()):
            c=m.group(1)+"-"+m.group(2)
            if c.replace("-","") not in {"WHATSAPP","DOWNLOAD","ANDROID","WINDOWS"}:
                return c
    return ""

def request_pair(phone):
    global PHONE,REQUEST
    p=re.sub(r"\D","",phone or "")
    if len(p)<7:raise ValueError("أدخل الرقم مع رمز الدولة، أرقام فقط.")
    PHONE=p;REQUEST=True
    setv(phone=p,requested=True,code="",stage="waiting_phone_login",
         message="تم استلام الرقم. ابحث عن «Log in with phone number»...")

def reset():
    global RESTART;RESTART=True

def loop():
    global REQUEST,RESTART
    back=3
    while True:
        d=None
        try:
            setv(ready=False,connected=False,code="",error=None,stage="starting",
                 message="التحقق من Xvfb ثم تشغيل Chrome...")
            d=make();setv(ready=True,stage="open_whatsapp",message="Chrome يعمل، فتح WhatsApp Web...")
            d.get("https://web.whatsapp.com/");back=3
            start_screens(d,.7)
            while True:
                if RESTART:RESTART=False;raise RuntimeError("Manual restart")
                try:setv(url=d.current_url,title=d.title,screenshot=snap(d))
                except:pass

                if connected(d):
                    setv(connected=True,code="",stage="connected",message="🟢 WhatsApp متصل")
                else:
                    setv(connected=False)
                    if REQUEST:
                        code=extract_code(d)
                        if code:
                            REQUEST=False
                            setv(code=code,stage="code_ready",message="🟢 تم العثور على كود الاقتران والتحقق منه")
                        elif S["stage"]=="waiting_phone_login":
                            if click_phone_login(d):
                                setv(stage="phone_input",message="تم الضغط على «Log in with phone number». انتظر خانة الرقم...")
                        elif S["stage"]=="phone_input":
                            inp=find_phone_input(d)
                            if inp:
                                inp.click();inp.send_keys(Keys.CONTROL+"a");inp.send_keys(PHONE)
                                if click_next(d):
                                    setv(stage="waiting_code",message="تم إدخال الرقم. جاري انتظار كود الاقتران...")
                                else:
                                    setv(stage="waiting_code",message="تم إدخال الرقم. اضغط Next إذا لم يتم تلقائيًا.")
                        elif S["stage"]=="waiting_code":
                            pass
                        else:
                            setv(stage="waiting_phone_login",message="في انتظار شاشة WhatsApp وزر «Log in with phone number»...")
                    else:
                        # No pairing request: do not touch the login controls.
                        setv(stage="idle",message="Chrome جاهز. أدخل رقم الهاتف لبدء الربط.")
                time.sleep(1.5)
        except Exception as e:
            msg=f"{type(e).__name__}: {e}";print("[WA]",msg,flush=True);traceback.print_exc()
            setv(ready=False,connected=False,code="",stage="error",error=msg,message="فشل Chrome — إعادة التشغيل...")
            stop_screens()
            try:
                if d:d.quit()
            except:pass
            time.sleep(back);back=min(back*2,45)
def start():threading.Thread(target=loop,name="whatsapp",daemon=True).start()
