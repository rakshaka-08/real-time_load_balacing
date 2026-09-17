import os
from datetime import timedelta
from dotenv import load_dotenv
from pathlib import Path


load_dotenv()

class Config:
    MONGO_URI = os.environ.get(
        "MONGO_URI",
        "mongodb://localhost:27017/",
    )
    MONGO_DB_NAME = os.environ.get(
        "MONGO_DB_NAME",
        "load_balancing",
    )
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    FRONTEND_ORIGIN = os.environ.get(
        "FRONTEND_ORIGIN",
        "http://localhost:5173",
    )