import os
from dotenv import load_dotenv

load_dotenv()

SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = os.getenv("SERVICE_PORT", 8000)