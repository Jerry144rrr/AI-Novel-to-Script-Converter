import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-6")
MAX_TOKENS_PER_REQUEST = 16000
# API 中转地址，直连 Anthropic 时设为空字符串 ""
BASE_URL = os.getenv("BASE_URL", "https://api.lmuai.com")
