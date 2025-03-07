import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5001")
