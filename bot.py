import os
import random
import threading
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
)

from database import (
    get_player,
    get_rank,
    load_players,
    save_players,
    update_level,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
SESSION_DIR = os.path.join(STORAGE_DIR, "whatsapp_session")
os.makedirs(SESSION_DIR, exist_ok=True)

players = load_players()
active_challenges = {}
state_lock = threading.Lock()
state = {
    "connected": False,
    "qr": None,
    "message": "جاري تشغيل WhatsApp...",
    "error": None,
}

CHALLENGES = [
    {"question": "🧠 التحدي الأول\n\nما الرقم التالي؟\n\n2 - 6 - 12 - 20 - 30 - ؟", "answers": ["42"], "points": 100},
    {"question": "🧠 التحدي الثاني\n\nشيء كلما أخذت منه كبر. ما هو؟", "answers": ["الحفرة", "حفرة"], "points": 100},
    {"question": "🧠 التحدي الثالث\n\nما الشيء الذي يمشي بلا أرجل؟", "answers": ["الوقت"], "points": 150},
]


def set_state(**kwargs):
    with state_lock:
        state.update(kwargs)


def get_state():
    with state_lock:
        return dict(state)


def normalize(text):
    return (text.strip().lower().replace("أ", "ا").replace("إ", "ا").replace("آ", "ا"))


def menu():
    return """╔════════════════════╗
       🎓 ELITE CLASS
╚════════════════════╝

/start — تسجيل الدخول
/profile — ملفك الشخصي
/challenge — تحدي جديد
/rank — المتصدرون
/help — المساعدة

⚠️ كل نقطة لها ثمن."""


def profile(player):
    return f"""╔════════════════════╗
       👤 PROFILE
╚════════════════════╝

الاسم: {player['name']}
💰 النقاط: {player['points']}
⭐ المستوى: {player['level']}
🎯 التحديات: {player['solved']}
🏆 الرتبة: {get_rank(player['points'])}"""


def ranking():
    if not players:
        return "لا يوجد لاعبون."
    top = sorted(players.values(), key=lambda x: x["points"], reverse=True)[:10]
    result = "╔════════════════════╗\n       🏆 TOP 10\n╚════════════════════╝\n\n"
    for i, player in enumerate(top, 1):
        result += f"{i}. {player['name']} — {player['points']} نقطة\n"
    return result


def create_driver():
    options = webdriver.ChromeOptions()
    options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/chromium")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--window-size=1365,900")
    options.add_argument("--user-data-dir=" + SESSION_DIR)
    options.add_argument("--remote-debugging-port=9222")
    return webdriver.Chrome(options=options)


def find_qr(driver):
    # WhatsApp Web has changed its DOM over time; try several likely QR containers.
    selectors = [
        "div[data-ref] canvas",
        "canvas",
    ]
    for selector in selectors:
        try:
            for element in driver.find_elements(By.CSS_SELECTOR, selector):
                if element.is_displayed():
                    image = element.screenshot_as_base64
                    if image:
                        return image
        except Exception:
            continue
    return None


def is_connected(driver):
    selectors = [
        "#side",
        "[data-testid='chat-list']",
        "[aria-label='Chat list']",
    ]
    for selector in selectors:
        try:
            element = driver.find_element(By.CSS_SELECTOR, selector)
            if element.is_displayed():
                return True
        except Exception:
            continue
    return False


def get_messages(driver):
    for selector in ("div.message-in", "div[data-testid='msg-container']"):
        try:
            messages = driver.find_elements(By.CSS_SELECTOR, selector)
            if messages:
                return messages
        except Exception:
            continue
    return []


def send_message(driver, text):
    for selector in ("footer div[contenteditable='true']", "div[contenteditable='true']"):
        try:
            for box in driver.find_elements(By.CSS_SELECTOR, selector):
                if box.is_displayed():
                    box.click()
                    box.send_keys(text)
                    box.send_keys(Keys.ENTER)
                    return True
        except Exception:
            continue
    return False


def process_message(driver, message):
    try:
        text = message.text.strip()
    except StaleElementReferenceException:
        return
    if not text:
        return

    # Prototype: one active player. Multi-player identity extraction comes next.
    player_id = "prototype-player"
    player = get_player(players, player_id, "Player")
    command = normalize(text)

    if command == "/start" or command == "/help":
        save_players(players)
        send_message(driver, menu())
        return
    if command == "/profile":
        send_message(driver, profile(player))
        return
    if command == "/rank":
        send_message(driver, ranking())
        return
    if command == "/challenge":
        challenge = random.choice(CHALLENGES)
        active_challenges[player_id] = challenge
        send_message(driver, f"╔════════════════════╗\n       ⚔️ CHALLENGE\n╚════════════════════╝\n\n{challenge['question']}\n\n━━━━━━━━━━━━━━━━━━━━\n🎯 الجائزة: {challenge['points']} نقطة\n\nأرسل إجابتك.")
        return

    challenge = active_challenges.get(player_id)
    if challenge:
        if any(command == normalize(answer) for answer in challenge["answers"]):
            player["points"] += challenge["points"]
            player["solved"] += 1
            update_level(player)
            save_players(players)
            del active_challenges[player_id]
            send_message(driver, f"🎯 إجابة صحيحة.\n\n+{challenge['points']} نقطة\n\n💰 نقاطك: {player['points']}\n⭐ المستوى: {player['level']}\n🏆 الرتبة: {get_rank(player['points'])}")
        else:
            send_message(driver, "❌ إجابة خاطئة.\n\nحاول مرة أخرى.")


def run_bot():
    last_signature = None
    while True:
        driver = None
        try:
            set_state(connected=False, qr=None, message="جاري تشغيل Chromium...", error=None)
            driver = create_driver()
            driver.get("https://web.whatsapp.com/")
            set_state(message="جاري تحميل WhatsApp Web...")

            while True:
                if is_connected(driver):
                    set_state(connected=True, qr=None, message="WhatsApp متصل", error=None)
                    messages = get_messages(driver)
                    if messages:
                        # Avoid repeatedly processing the same visible last message.
                        try:
                            signature = messages[-1].text.strip()
                        except Exception:
                            signature = None
                        if signature and signature != last_signature:
                            last_signature = signature
                            process_message(driver, messages[-1])
                else:
                    qr = find_qr(driver)
                    if qr:
                        set_state(connected=False, qr=qr, message="امسح QR من هاتفك", error=None)
                    else:
                        set_state(connected=False, qr=None, message="جاري إنشاء QR...", error=None)
                time.sleep(2)
        except Exception as error:
            print("BOT ERROR:", repr(error), flush=True)
            set_state(connected=False, qr=None, message="إعادة تشغيل WhatsApp...", error=str(error))
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass
            time.sleep(10)


threading.Thread(target=run_bot, daemon=True, name="whatsapp-selenium").start()
