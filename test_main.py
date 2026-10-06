import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_USER = {
    "username": "crud_devops_user",
    "password": "superpassword123"
}

TEST_ITEM = {
    "title": "Изучить DevOps",
    "description": "Пройти настройку CI/CD и Grafana"
}


def test_full_application_flow():
    """Полный тест: Регистрация -> Логин -> CRUD над Items -> /users/me"""
    
    # 1. Регистрация юзера
    res_reg = client.post("/register", json=TEST_USER)
    assert res_reg.status_code in [201, 400]

    # 2. Логин и получение JWT
    res_login = client.post("/login", data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    })
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Проверка /users/me
    res_me = client.get("/users/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["username"] == TEST_USER["username"]

    # 4. CREATE: Создание Item с переданным токеном
    res_create = client.post("/items/", json=TEST_ITEM, headers=headers)
    assert res_create.status_code == 201
    created_item = res_create.json()
    assert created_item["title"] == TEST_ITEM["title"]
    assert created_item["completed"] is False
    item_id = created_item["id"]

    # 5. READ: Получение списка Items юзера
    res_list = client.get("/items/", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) > 0

    # 6. READ: Получение точечного Item по ID
    res_get = client.get(f"/items/{item_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == item_id

    # 7. DELETE: Удаление Item
    res_del = client.delete(f"/items/{item_id}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json() == {"detail": "Item deleted"}

    # 8. VERIFY DELETE: Проверка 404 после удаления
    res_del_check = client.get(f"/items/{item_id}", headers=headers)
    assert res_del_check.status_code == 404


def test_unauthorized_items_access():
    """Проверка блокировки запросов без токена"""
    res = client.post("/items/", json=TEST_ITEM)
    assert res.status_code == 401