import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("No se encontró DATABASE_URL en el archivo .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=False,
    pool_size=5,
    max_overflow=5,
    pool_recycle=300,
    pool_use_lifo=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def obtener_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
