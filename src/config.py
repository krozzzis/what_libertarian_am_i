import os


class Config:
    BOT_TOKEN=os.getenv("BOT_TOKEN")
    QUIZ_PATH=os.getenv("QUIZ_PATH", default="data/quiz.json5")
    PARTY_URL = os.getenv("PARTY_URL", "http://t.me/lpr_website_bot/join")
