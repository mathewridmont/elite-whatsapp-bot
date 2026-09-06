import json
import os
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "storage", "data", "players.json")
LOCK = threading.Lock()


def init_database():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_players():
    init_database()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_players(players):
    init_database()
    with LOCK:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(players, f, ensure_ascii=False, indent=2)
        os.replace(tmp, DATA_FILE)


def get_player(players, player_id, name):
    if player_id not in players:
        players[player_id] = {
            "name": name,
            "points": 0,
            "level": 1,
            "solved": 0,
        }
    else:
        players[player_id]["name"] = name
    return players[player_id]


def update_level(player):
    player["level"] = player["points"] // 100 + 1


def get_rank(points):
    if points >= 1000:
        return "👑 العبقري"
    if points >= 700:
        return "🔥 النخبة"
    if points >= 400:
        return "⚔️ المتقدم"
    if points >= 200:
        return "🎯 المحترف"
    return "🟢 المبتدئ"
