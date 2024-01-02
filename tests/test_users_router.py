import sys
import json

import jwt
import pytest

from fastapi import status

sys.path.append('./src/')
from api.constants import JWT_KEY, ALGORITHM


@pytest.mark.unit
def test_get_token_unauthorized(test_app, token_nothing):
    response = test_app.post(url='/users/token',
                             data={'username': 'nothing', 'password': 'nothing', 'scope': ''},
                             headers={"content-type": "application/x-www-form-urlencoded"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == '{"detail":"Incorrect username or password"}'


@pytest.mark.unit
def test_get_token(test_app, token_admin):
    response = token_admin
    payload = jwt.decode(response['access_token'], JWT_KEY, algorithms=[ALGORITHM])

    assert payload.get('sub') == 'admin'
    assert payload.get('scopes') == ['USERS:READ', 'USERS:WRITE']


@pytest.mark.unit
def test_add_user(test_app, token_admin):
    token = token_admin
    data = {'id': 2, 'name': 'test_add_user', 'username': 'test_add_user', 'password': 'test_add_user', 'scopes': '',
            'is_admin': 0, 'enabled': 1}
    response = test_app.post(url='/users/add',
                             data=json.dumps(data),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == 200
    assert response.json() == "User with username test_add_user has successfully been added to the DB"


@pytest.mark.unit
def test_add_user_duplicate(test_app, token_admin):
    token = token_admin
    data = {'id': 5, 'name': 'admin', 'username': 'admin', 'password': 'admin', 'scopes': '', 'is_admin': 0,
            'enabled': 1}
    response = test_app.post(url='/users/add',
                             data=json.dumps(data),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == 400
    assert response.json() == {"detail": "A user with username admin already exists"}
