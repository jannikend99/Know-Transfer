from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Attempt to load environment variables if python-dotenv is available
# Fallback to os.environ.get for environments where .env is pre-loaded
try:
    from dotenv import load_dotenv
    # Look for .env file in the root directory (three levels up from this file)
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
except ImportError:
    print("python-dotenv not installed, skipping .env file loading. Ensure environment variables are set.")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./knowledge_transfer.db")
UPLOAD_DIRECTORY = os.environ.get("UPLOAD_DIRECTORY", "./uploads_default")
VECTOR_STORE_PATH = os.environ.get("VECTOR_STORE_PATH", "./vector_store_default")

# Create upload directory if it doesn't exist
if not os.path.exists(UPLOAD_DIRECTORY):
    try:
        os.makedirs(UPLOAD_DIRECTORY)
        print(f"Created upload directory: {UPLOAD_DIRECTORY}")
    except OSError as e:
        print(f"Error creating upload directory {UPLOAD_DIRECTORY}: {e}")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} # check_same_thread is for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 