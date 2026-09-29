import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="DevOps Pet Project")

# Получаем настройки подключения к БД из переменных окружения (Environment Variables)
DB_USER = os.getenv("POSTGRES_USER", "devops_user") 
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "devops_pass")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "devops_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

@app.get("/")
def read_root():
    return {"message": "Hello, Kazakhstan DevOps!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "backend"}

@app.get("/db-check")
def db_check():
    """Эндпоинт для проверки связи с базой данных PostgreSQL"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            db_version = result.scalar()
        return {
            "status": "connected",
            "database": DB_NAME,
            "version": db_version
        }
    except Exception as e:
        return {
            "status": "error",
            "details": str(e)
        }

Instrumentator().instrument(app).expose(app)

@app.get("/")
def read_root():
    return {"message": "DevOps App is Running!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}