# backend/app/core/config.py
import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  
env_path = BASE_DIR / '.env'

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✓ Loaded .env from: {env_path}")
else:
    print("⚠️  No .env file found - using environment variables from Docker")

class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "")
    
    # Construct database URL
    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.DB_PASSWORD)
        return f"postgresql://{self.DB_USER}:{encoded_password}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Alternative database URL (without URL encoding)
    @property
    def DATABASE_URL_RAW(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def validate(self):
        """Validate that all required settings are present"""
        missing = []
        if not self.DB_HOST: missing.append("DB_HOST")
        if not self.DB_USER: missing.append("DB_USER")
        if not self.DB_PASSWORD: missing.append("DB_PASSWORD")
        if not self.DB_NAME: missing.append("DB_NAME")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        print(f"✓ Database configured for: {self.DB_NAME}")
        return True

# Create settings instance
settings = Settings()

# Validate on import
try:
    settings.validate()
except ValueError as e:
    print(f"❌ Configuration error: {e}")
    print(f"   Environment variables needed: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME")
    raise