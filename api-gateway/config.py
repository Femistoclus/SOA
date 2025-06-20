import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5001")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_VERIFY_SUB = False

    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5001")
    POST_SERVICE_GRPC = os.getenv("POST_SERVICE_GRPC", "post-service:50051")
