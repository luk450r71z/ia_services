import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "adaptiera_super_secret_key_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# API Configuration
API_VERSION = "1.0.0"
API_TITLE = "AI Services Authentication API"
API_DESCRIPTION = "API for discovering and authenticating AI services" 