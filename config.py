import os
BASE=os.path.dirname(os.path.abspath(__file__))
STORAGE=os.path.join(BASE,"storage")
SESSION=os.path.join(STORAGE,"whatsapp_session")
DEBUG=os.path.join(STORAGE,"debug")
os.makedirs(SESSION,exist_ok=True);os.makedirs(DEBUG,exist_ok=True)
ADMIN_USER=os.getenv("ADMIN_USER","admin")
ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD","change-me")
SECRET=os.getenv("FLASK_SECRET_KEY","change-me")
