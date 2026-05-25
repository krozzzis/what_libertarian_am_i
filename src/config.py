import os


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    QUIZ_PATH = os.getenv("QUIZ_PATH", default="data/quiz.json5")
    PARTY_URL = os.getenv("PARTY_URL", "http://t.me/lpr_website_bot/join")
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    LOG_FILE = os.getenv("LOG_FILE", default="logs/bot.log")
    LOG_ROTATION = os.getenv("LOG_ROTATION", default="10 MB")
    LOG_RETENTION = os.getenv("LOG_RETENTION", default="10 days")
    LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")