"""
Central config — loads env vars and defines constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])

GEMINI_MODEL = "gemini-2.5-flash"
