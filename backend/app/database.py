from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

print(f"🔧 Using database: {settings.DB_NAME}")

# Try both URL formats
SQLALCHEMY_DATABASE_URLS = [
    settings.DATABASE_URL,      # URL encoded
    settings.DATABASE_URL_RAW,  # Raw (no encoding)
]

engine = None
SQLALCHEMY_DATABASE_URL = None

for i, db_url in enumerate(SQLALCHEMY_DATABASE_URLS):
    try:
        safe_url = db_url.replace(settings.DB_PASSWORD, '***')
        print(f"\n🔄 Attempt {i+1}: {safe_url}")
        
        engine = create_engine(db_url)
        
        # Test connection with text() wrapper
        with engine.connect() as conn:
            # Test 1: Check PostgreSQL version
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"   ✅ PostgreSQL: {version.split(',')[0]}")
            
            # Test 2: Check if our database exists
            result = conn.execute(text("SELECT datname FROM pg_database WHERE datname = :db_name"), 
                                 {"db_name": settings.DB_NAME})
            db_exists = result.fetchone() is not None
            
            if db_exists:
                print(f"   ✅ Database '{settings.DB_NAME}' exists")
            else:
                print(f"   ⚠️  Database '{settings.DB_NAME}' does not exist")
                print(f"      Run: CREATE DATABASE \"{settings.DB_NAME}\";")
            
            # Test 3: Check current database
            result = conn.execute(text("SELECT current_database();"))
            current_db = result.fetchone()[0]
            print(f"   📊 Connected to database: {current_db}")
            
            SQLALCHEMY_DATABASE_URL = db_url
            print(f"   🎉 Connection successful!")
            break
            
    except Exception as e:
        print(f"   ❌ Attempt {i+1} failed: {str(e)[:100]}...")
        continue

if engine is None:
    print(f"\n❌ All connection attempts failed")
    print(f"   Check your PostgreSQL is running: net start postgresql")
    print(f"   Check credentials in .env file")
    raise ConnectionError("Failed to connect to database")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print(f"\n✨ Database module initialized successfully")
