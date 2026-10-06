import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Тестовые данные юзера
TEST_USER = {
    "username": "testuser_ci",
    "password": "testpassword123"
}

def test_metrics_and_docs():
    """1. Проверка служебных эндпоинтов"""
    res_metrics = client.get("/metrics")
    assert res_metrics.status_code == 200

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200


def test_user_flow():
    """2. Комплексный тест: Регистрация -> Логин -> Доступ к /users/me"""
    
    # Шаг A: Регистрация
    response_reg = client.post("/register", json=TEST_USER)
    # Если юзер уже есть в тестовой БД, допускаем статус 200 или 400 (User already exists)
    assert response_reg.status_code in [200, 400]

    # Шаг B: Логин и получение JWT-токена
    response_login = client.post("/login", data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    })
    assert response_login.status_code == 200
    data = response_login.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    token = data["access_token"]

    # Шаг C: Запрос к защищенному эндпоинту /users/me С токеном
    headers = {"Authorization": f"Bearer {token}"}
    response_me = client.get("/users/me", headers=headers)
    assert response_me.status_code == 200
    assert response_me.json()["username"] == TEST_USER["username"]


def test_unauthorized_access():
    """3. Проверка защиты: запрос к /users/me БЕЗ токена должен отдавать 401"""
    response = client.get("/users/me")
    assert response.status_code == 401