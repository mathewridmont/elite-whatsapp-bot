import os,time,threading
DEBUG_DIR=os.getenv("DEBUG_DIR","/app/storage/debug");os.makedirs(DEBUG_DIR,exist_ok=True)
PATH=os.path.join(DEBUG_DIR,"whatsapp.png")
_running=False;_thread=None
def take(driver):
    if driver is None:return False
    try:
        if not driver.window_handles:return False
        driver.switch_to.window(driver.window_handles[0])
        tmp=PATH+".tmp"
        if driver.save_screenshot(tmp) and os.path.exists(tmp):
            os.replace(tmp,PATH);return True
    except Exception as e:print("[SCREENSHOT]",type(e).__name__,e,flush=True)
    return False
def loop(driver,interval=.7):
    global _running
    _running=True
    while _running:
        take(driver);time.sleep(interval)
def start(driver,interval=.7):
    global _thread
    if _thread and _thread.is_alive():return
    _thread=threading.Thread(target=loop,args=(driver,interval),daemon=True);_thread.start()
def stop():
    global _running
    _running=False
