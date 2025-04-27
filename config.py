import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "superSecretKey")
    # Prefer the hosting service's DATABASE_URL if available.
    _database_url = os.environ.get("DATABASE_URL")
    if _database_url:
        # Convert the URI scheme if needed
        SQLALCHEMY_DATABASE_URI = _database_url.replace("postgres://", "postgresql://", 1)
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///user.db")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
    MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")