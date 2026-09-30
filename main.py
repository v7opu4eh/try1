import os
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from prometheus_fastapi_instrumentator import Instrumentator
import time
import random


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

@app.get("/slow")
def slow_endpoint():
    delay = random.uniform(0.5, 3)  # Задержка от 0.5 до 2.5 секунд
    time.sleep(delay)
    return {"message": f"Response delayed by {delay:.2f} seconds"}

# 2. Эндпоинт со случайной ошибкой 500 (для проверки алертов и ошибок)
@app.get("/error")
def error_endpoint():
    if random.random() < 0.7:  # 70% вероятность ошибки
        raise HTTPException(status_code=500, detail="Simulated Internal Server Error")
    return {"message": "Lucky this time! No error."}