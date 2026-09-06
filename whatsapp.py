import os,time,re,threading,traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from config import SESSION,DEBUG

LOCK=threading.RLock()
D={"connected":False,"ready":False,"message":"لم يبدأ Selenium بعد","error":None,
   "url":"","title":"","phone":"","pairing_code":"","pairing_requested":False,
   "screenshot":"","updated":0}
DRIVER=None
PHONE=""
REQUEST=False
RESTART=False

def state():
    with LOCK:return dict(D)

def setd(**kw):
    with LOCK:
        D.update(kw);D["updated"]=time.time()

def options():
    o=webdriver.ChromeOptions()
    o.binary_location=os.getenv("CHROME_BIN","/usr/bin/chromium")
    for a in ["--no-sandbox","--disable-dev-shm-usage","--disable-gpu",
              "--window-size=1440,1000","--disable-extensions","--disable-notifications",
              "--no-first-run","--no-default-browser-check","--disable-popup-blocking"]:
        o.add_argument(a)
    o.add_argument("--lang=en-US")
    o.add_argument(f"--user-data-dir={SESSION}")
    return o

def text_all(d):
    try:return d.find_element(By.TAG_NAME,"body").text
    except:return ""

def screenshot(d):
    try:
        p=os.path.join(DEBUG,"whatsapp.png");d.save_screenshot(p)
        return "/debug/whatsapp.png?"+str(int(time.time()))
    except:return ""

def find_pair_button(d):
    # Exact/partial English labels first, then Arabic.
    xpaths=[
      "//*[self::button or @role='button'][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'link with phone number')]",
      "//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'link with phone number')]",
      "//*[contains(normalize-space(.),'ربط برقم الهاتف')]"
    ]
    for xp in xpaths:
        try:
            for e in d.find_elements(By.XPATH,xp):
                if e.is_displayed():
                    d.execute_script("arguments[0].click();",e); return True
        except: pass
    return False

def find_phone_input(d):
    sels=["input[type='tel']","input[placeholder*='phone']","input[placeholder*='Phone']",
          "input[aria-label*='phone']","input[aria-label*='Phone']"]
    for s in sels:
        try:
            for e in d.find_elements(By.CSS_SELECTOR,s):
                if e.is_displayed(): return e
        except:pass
    return None

def find_continue(d):
    for xp in [
      "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next')]",
      "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'continue')]",
      "//*[self::button or @role='button'][contains(normalize-space(.),'متابعة')]"
    ]:
        try:
            for e in d.find_elements(By.XPATH,xp):
                if e.is_displayed():
                    d.execute_script("arguments[0].click();",e);return True
        except:pass
    return False

def extract_code(d):
    body=text_all(d)
    # Pairing codes are normally an 8-character alphanumeric string, often grouped.
    patterns=[
      r"\b([A-Z0-9]{4}[-\s][A-Z0-9]{4})\b",
      r"\b([A-Z0-9]{8})\b"
    ]
    for p in patterns:
        for m in re.findall(p,body,re.I):
            c=re.sub(r"\s+","-",m.upper())
            if c not in {"WHATSAPP","DOWNLOAD","ANDROID"}:
                return c
    # Look at inputs/labels that may contain the generated code.
    try:
        for e in d.find_elements(By.CSS_SELECTOR,"input,code"):
            v=(e.get_attribute("value") or e.text or "").strip()
            if re.fullmatch(r"[A-Za-z0-9]{4}[-\s]?[A-Za-z0-9]{4}",v):
                return re.sub(r"\s+","-",v.upper())
    except:pass
    return ""

def request_pairing(phone):
    global PHONE,REQUEST
    phone=re.sub(r"\D","",phone or "")
    if len(phone)<7: raise ValueError("أدخل رقم WhatsApp مع رمز الدولة، أرقام فقط.")
    PHONE=phone;REQUEST=True
    setd(phone=phone,pairing_requested=True,pairing_code="",error=None,message="سيتم طلب كود الاقتران...")

def reset():
    global RESTART
    RESTART=True

def loop():
    global DRIVER,REQUEST,RESTART
    back=3
    while True:
        d=None
        try:
            setd(ready=False,connected=False,pairing_code="",message="تشغيل Chromium...")
            d=webdriver.Chrome(options=options());DRIVER=d
            setd(ready=True,message="فتح WhatsApp Web...")
            d.get("https://web.whatsapp.com/")
            back=3
            while True:
                if RESTART:
                    RESTART=False
                    raise RuntimeError("Manual restart")
                setd(url=d.current_url,title=d.title)
                body=text_all(d)

                if any(x in body.lower() for x in ["chats","archived","status","communities"]) or \
                   any(d.find_elements(By.CSS_SELECTOR,s) for s in ["#side","[data-testid='chat-list']"]):
                    setd(connected=True,pairing_code="",message="🟢 WhatsApp متصل")
                else:
                    if REQUEST and not D.get("pairing_code"):
                        inp=find_phone_input(d)
                        if inp:
                            inp.click();inp.send_keys(Keys.CONTROL+"a");inp.send_keys(PHONE)
                            find_continue(d)
                            REQUEST=False
                            setd(message="تم إرسال الرقم إلى WhatsApp، في انتظار كود الاقتران...")
                        else:
                            if find_pair_button(d):
                                setd(message="تم فتح خيار الربط برقم الهاتف...")
                            else:
                                setd(message="لم يظهر خيار «الربط برقم الهاتف» في WhatsApp Web. اللقطة أدناه توضح الصفحة الحالية.")
                    code=extract_code(d)
                    if code:setd(pairing_code=code,message="🟢 كود الاقتران جاهز — أدخله في هاتفك داخل WhatsApp.")
                    setd(screenshot=screenshot(d))
                time.sleep(2)
        except Exception as e:
            print("[WA]",repr(e),flush=True);traceback.print_exc()
            setd(ready=False,connected=False,error=f"{type(e).__name__}: {e}",message="تعطل Selenium — إعادة التشغيل...")
            try:
                if d:d.quit()
            except:pass
            time.sleep(back);back=min(back*2,45)
        finally: DRIVER=None

def start():
    threading.Thread(target=loop,name="whatsapp",daemon=True).start()
