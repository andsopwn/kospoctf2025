from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import get_setting
import os

settings = get_setting()

SQLALCHEMY_DATABASE_URL = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(
    os.getenv('DB_USER', 'root'),
    os.getenv('DB_PASSWORD', 'root'),
    os.getenv('DB_HOST', 'chall_db'),
    os.getenv('DB_PORT', '3306'),
    os.getenv('DB_NAME', 'mydb'),
)

db_engine = create_engine(SQLALCHEMY_DATABASE_URL) # SQLAlchemy 엔진 객체 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine) # 동일한 구성을 가진 세션을 생성하는 factory

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()