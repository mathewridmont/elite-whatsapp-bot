import os,time,base64,threading,traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from config import SESSION,DEBUG

LOCK=threading.RLock()
DATA={"connected":False,"message":"جاري تشغيل Chromium...","error":None,
      "qr":None,"screenshot":None,"url":"","title":"","chrome":False,
      "page_loaded":False,"qr_source":"none","updated":0}
DRIVER=None
RESTART=False

def setd(**kw):
    with LOCK:
        DATA.update(kw); DATA["updated"]=time.time()

def state():
    with LOCK:return dict(DATA)

def options():
    o=webdriver.ChromeOptions()
    o.binary_location=os.getenv("CHROME_BIN","/usr/bin/chromium")
    for a in [
        "--no-sandbox","--disable-dev-shm-usage","--disable-gpu",
        "--window-size=1440,1000","--disable-extensions","--disable-notifications",
        "--no-first-run","--no-default-browser-check","--disable-background-networking",
        "--disable-popup-blocking"
    ]: o.add_argument(a)
    o.add_argument("--lang=en-US")
    o.add_argument(f"--user-data-dir={SESSION}")
    return o

def visible(d,s):
    try:return [x for x in d.find_elements(By.CSS_SELECTOR,s) if x.is_displayed()]
    except:return []

def is_connected(d):
    return any(visible(d,s) for s in [
        "#side","[data-testid='chat-list']","[aria-label='Chat list']",
        "[aria-label='قائمة الدردشات']"
    ])

def element_qr(d):
    # Capture likely QR elements without depending on one exact selector.
    selectors=[
        "canvas","div[data-ref]","div[data-testid*='qr']",
        "img[alt*='QR']","img[alt*='qr']","img[alt*='رمز']"
    ]
    for s in selectors:
        for e in visible(d,s):
            try:
                b=e.screenshot_as_png
                if b and len(b)>1200:
                    return base64.b64encode(b).decode(),"element:"+s
            except: pass
    return None,"none"

def full_screenshot(d):
    try:
        p=os.path.join(DEBUG,"whatsapp.png")
        d.save_screenshot(p)
        with open(p,"rb") as f:return base64.b64encode(f.read()).decode()
    except:return None

def click_phone_link(d):
    # Best-effort: expose phone-number pairing UI if WhatsApp offers it.
    texts=["Link with phone number","link with phone number","ربط برقم الهاتف"]
    for t in texts:
        try:
            els=d.find_elements(By.XPATH,f"//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{t.lower()}')]")
            for e in els:
                if e.is_displayed():
                    e.click(); return True
        except: pass
    return False

def reset_session():
    global RESTART
    RESTART=True

def run():
    global DRIVER,RESTART
    backoff=3
    while True:
        d=None
        try:
            setd(connected=False,qr=None,screenshot=None,message="بدء Chromium عبر Xvfb...",error=None,chrome=False,page_loaded=False)
            d=webdriver.Chrome(options=options()); DRIVER=d
            setd(chrome=True,message="Chromium يعمل، فتح WhatsApp Web...")
            d.get("https://web.whatsapp.com/")
            setd(page_loaded=True,url=d.current_url,title=d.title,message="WhatsApp Web تم فتحه، جاري فحص الشاشة...")
            backoff=3
            while True:
                if RESTART:
                    RESTART=False
                    raise RuntimeError("Manual WhatsApp restart requested")
                try:
                    setd(url=d.current_url,title=d.title)
                except: pass

                if is_connected(d):
                    setd(connected=True,qr=None,message="🟢 WhatsApp متصل",qr_source="none")
                else:
                    q,source=element_qr(d)
                    shot=full_screenshot(d)
                    # Always provide a screenshot for diagnostics. QR page can show it if element QR isn't found.
                    setd(connected=False,qr=q,screenshot=shot,
                         message="امسح رمز QR من شاشة الربط" if q else "WhatsApp مفتوح، لم يتم التعرف على عنصر QR — اعرض اللقطة للتشخيص",
                         qr_source=source)
                time.sleep(2)
        except Exception as e:
            print("[WA ERROR]",repr(e),flush=True);traceback.print_exc()
            setd(connected=False,qr=None,message="تعطل Selenium — إعادة التشغيل...",error=f"{type(e).__name__}: {e}")
            try:
                if d:d.quit()
            except:pass
            time.sleep(backoff);backoff=min(backoff*2,45)
        finally: DRIVER=None

def start():
    threading.Thread(target=run,name="whatsapp",daemon=True).start()
