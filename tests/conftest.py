import pytest

from fastapi.testclient import TestClient
# from fastapi_pagination import add_pagination


@pytest.fixture()
def test_app():
    from api.main import app, add_pagination
    add_pagination(app)
    client = TestClient(app)
    yield client


@pytest.fixture()
def token_admin(test_app):
    response = test_app.post(url='/user/token', data={'username': 'admin',
                                                      'password': 'admin',
                                                      'scope': 'USERS:READ'},
                             headers={"content-type": "application/x-www-form-urlencoded"})
    return response.json()
