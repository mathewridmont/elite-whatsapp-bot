import os,re,time,threading,subprocess,traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from config import SESSION,DEBUG

LOCK=threading.RLock()
S={"connected":False,"ready":False,"message":"بدء Chrome...","error":None,"phone":"","code":"",
   "requested":False,"url":"","title":"","chrome":"","driver":"","screenshot":"","updated":0}
PHONE=""; REQUEST=False; RESTART=False

def setv(**kw):
    with LOCK:S.update(kw);S["updated"]=time.time()
def state():
    with LOCK:return dict(S)

def cmd(c):
    try:return subprocess.check_output(c,stderr=subprocess.STDOUT,text=True,timeout=10).strip()
    except Exception as e:return "unavailable: "+str(e)

def options():
    o=webdriver.ChromeOptions();o.binary_location=os.getenv("CHROME_BIN","/usr/bin/chromium")
    for a in ["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage","--disable-gpu",
              "--disable-software-rasterizer","--window-size=1365,900","--disable-extensions",
              "--disable-notifications","--no-first-run","--no-default-browser-check",
              "--disable-popup-blocking","--disable-background-networking","--disable-sync",
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
    d=webdriver.Chrome(service=service,options=options());d.set_page_load_timeout(120);return d

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

def visible_text_nodes(d):
    # Collect visible elements containing a plausible pairing code, while excluding generic page words.
    vals=[]
    try:
        els=d.find_elements(By.XPATH,"//*[normalize-space(text())!='']")
        for e in els:
            try:
                if not e.is_displayed():continue
                t=" ".join((e.text or "").split())
                if 5<=len(t)<=30: vals.append(t)
            except:pass
    except:pass
    return vals

def extract_code(d):
    candidates=visible_text_nodes(d)+[body(d)]
    pats=[
      r"\b([A-Z0-9]{4})[\s-]+([A-Z0-9]{4})\b",
      r"\b([A-Z0-9]{8})\b"
    ]
    banned={"WHATSAPP","DOWNLOAD","ANDROID","WINDOWS","CONTINUE","NEXT","PHONE","NUMBER"}
    for text in candidates:
        for p in pats:
            m=re.search(p,text,re.I)
            if m:
                c=(m.group(1)+"-"+m.group(2)).upper() if len(m.groups())==2 else m.group(1).upper()
                if c.replace("-","") not in banned and len(c.replace("-",""))==8:
                    return c
    # Sometimes the code is exposed through aria-label/title/value rather than text.
    try:
        for e in d.find_elements(By.CSS_SELECTOR,"[aria-label],[title],input"):
            if not e.is_displayed():continue
            for v in [e.get_attribute("aria-label"),e.get_attribute("title"),e.get_attribute("value")]:
                if not v:continue
                m=re.search(r"\b([A-Z0-9]{4})[\s-]+([A-Z0-9]{4})\b",v,re.I)
                if m:return (m.group(1)+"-"+m.group(2)).upper()
    except:pass
    return ""

def click_pair(d):
    xps=[
      "//*[self::button or @role='button'][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'link with phone number')]",
      "//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'link with phone number')]",
      "//*[contains(normalize-space(.),'ربط برقم الهاتف')]"
    ]
    for xp in xps:
        try:
            for e in d.find_elements(By.XPATH,xp):
                if e.is_displayed():d.execute_script("arguments[0].click();",e);return True
        except:pass
    return False

def phone_input(d):
    for s in ["input[type='tel']","input[placeholder*='phone']","input[placeholder*='Phone']","input[aria-label*='phone']"]:
        try:
            for e in d.find_elements(By.CSS_SELECTOR,s):
                if e.is_displayed():return e
        except:pass
    return None

def click_continue(d):
    for xp in ["//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next')]",
               "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue')]",
               "//*[self::button or @role='button'][contains(normalize-space(.),'متابعة')]"]:
        try:
            for e in d.find_elements(By.XPATH,xp):
                if e.is_displayed():d.execute_script("arguments[0].click();",e);return True
        except:pass
    return False

def request_pair(phone):
    global PHONE,REQUEST
    p=re.sub(r"\D","",phone or "")
    if len(p)<7:raise ValueError("الرقم غير صالح. استخدم رمز الدولة وأرقامًا فقط.")
    PHONE=p;REQUEST=True
    setv(phone=p,requested=True,code="",error=None,message="تم استلام الرقم، انتظر تجهيز شاشة الاقتران...")

def reset():
    global RESTART
    RESTART=True

def loop():
    global REQUEST,RESTART
    back=3
    while True:
        d=None
        try:
            setv(ready=False,connected=False,code="",error=None,message="التحقق من Xvfb ثم تشغيل Chrome...")
            d=make();setv(ready=True,message="Chrome يعمل، فتح WhatsApp Web...")
            d.get("https://web.whatsapp.com/");back=3
            while True:
                if RESTART:RESTART=False;raise RuntimeError("Manual restart")
                try:setv(url=d.current_url,title=d.title)
                except:pass
                if connected(d):
                    setv(connected=True,code="",message="🟢 WhatsApp متصل",screenshot=snap(d))
                else:
                    setv(connected=False,screenshot=snap(d))
                    if REQUEST and not S["code"]:
                        inp=phone_input(d)
                        if inp:
                            inp.click();inp.send_keys(Keys.CONTROL+"a");inp.send_keys(PHONE)
                            if click_continue(d):
                                REQUEST=False;setv(message="تم إرسال الرقم إلى WhatsApp، جاري انتظار كود الاقتران...")
                        elif click_pair(d):
                            setv(message="تم فتح خيار الربط برقم الهاتف...")
                        else:
                            setv(message="لم يظهر خيار الربط بالرقم بعد.")
                    c=extract_code(d)
                    if c:setv(code=c,message="🟢 تم التحقق من وجود كود اقتران فعلي")
                time.sleep(2)
        except Exception as e:
            msg=f"{type(e).__name__}: {e}";print("[WA]",msg,flush=True);traceback.print_exc()
            setv(ready=False,connected=False,code="",error=msg,message="فشل Chrome — إعادة التشغيل...",screenshot=snap(d) if d else "")
            try:
                if d:d.quit()
            except:pass
            time.sleep(back);back=min(back*2,45)

def start():threading.Thread(target=loop,name="whatsapp",daemon=True).start()
