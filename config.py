from datetime import timedelta

import os

from dotenv import load_dotenv



load_dotenv()



class Config:

    SECRET_KEY = os.getenv('SECRET_KEY')

    

    # MongoDB settings

    MONGODB_SETTINGS = {

        'db': os.getenv('MONGO_DB', 'polling_app'),

        'host': os.getenv('MONGO_HOST', 'mongodb://localhost:27017/'),

        'connect': True,

        'authentication_source': 'admin'  # Add this if using authentication

    }

    

    # OAuth 2.0 Settings

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

    GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

    

    # Mail settings

    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')

    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))

    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'

    MAIL_USERNAME = os.getenv('MAIL_USERNAME')

    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')

    

    # Token expiration

    VERIFY_EMAIL_TOKEN_EXPIRY = timedelta(hours=24)

    RESET_PASSWORD_TOKEN_EXPIRY = timedelta(hours=1)

    

    # Session settings

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    

    # Upload settings

    UPLOAD_FOLDER = os.path.join('static', 'uploads')

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    

    # Application settings

    POLLS_PER_PAGE = 12

    VERIFY_EMAIL_EXPIRATION = 24  # hours

    RESET_PASSWORD_EXPIRATION = 1  # hours

    

    # API settings

    API_RATE_LIMIT = '100 per minute'


