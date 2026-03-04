import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token (from @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Channel ID (negative number, e.g. -1001234567890)
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# Admin Telegram IDs (can unban users)
_admin_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in _admin_ids.split(",") if x.strip()]

# Web panel settings
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
WEB_SECRET = os.getenv("WEB_SECRET", "change_this_secret_password")
