import os
import time
import random
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

from sqlalchemy import create_engine, text, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

import jwt
from pwdlib import PasswordHash

# 1. Настройки БД и JWT
POSTGRES_USER = os.getenv("POSTGRES_USER", "devops_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "devops_pass")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "devops_db")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_devops_key_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# 2. Инициализация SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Модели БД
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    items = relationship("ItemDB", back_populates="owner")

class ItemDB(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("UserDB", back_populates="items")

Base.metadata.create_all(bind=engine)

# 4. Pydantic-схемы
class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None

class ItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool
    owner_id: Optional[int] = None

    class Config:
        from_attributes = True

# 5. Хелперы безопасности (Объявлены СТРОГО до вызова в эндпоинтах)
def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 6. Инициализация FastAPI приложения
app = FastAPI(title="DevOps Practice App with DB & Auth")
Instrumentator().instrument(app).expose(app)

# Зависимости
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен доступа",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# 7. Базовые / Служебные эндпоинты
@app.get("/")
def read_root():
    return {"message": "As-Salaymu Aleikum"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "backend"}

@app.get("/db-check")
def db_check():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            db_version = result.scalar()
        return {
            "status": "connected",
            "database": POSTGRES_DB,
            "version": db_version
        }
    except Exception as e:
        return {
            "status": "error",
            "details": str(e)
        }

@app.get("/slow")
def slow_endpoint():
    delay = random.uniform(0.5, 3)
    time.sleep(delay)
    return {"message": f"Response delayed by {delay:.2f} seconds"}

@app.get("/error")
def error_endpoint():
    if random.random() < 0.7:
        raise HTTPException(status_code=500, detail="Simulated Internal Server Error")
    return {"message": "Lucky this time! No error."}

# 8. Эндпоинты авторизации
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
    
    hashed_pwd = hash_password(user.password)
    new_user = UserDB(username=user.username, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# 9. Защищённые CRUD эндпоинты
@app.post("/items/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)):
    db_item = ItemDB(title=item.title, description=item.description, owner_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items/", response_model=List[ItemResponse])
def read_items(db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)):
    return db.query(ItemDB).filter(ItemDB.owner_id == current_user.id).all()

@app.get("/items/{item_id}", response_model=ItemResponse)
def read_item(item_id: int, db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)):
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id, ItemDB.owner_id == current_user.id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)):
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id, ItemDB.owner_id == current_user.id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"detail": "Item deleted"}

@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: UserDB = Depends(get_current_user)):
    """Возвращает информацию о текущем авторизованном пользователе"""
    return current_user