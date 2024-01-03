import json

import jwt
import pytest

from fastapi import status, HTTPException

from api.constants import JWT_KEY, ALGORITHM


@pytest.mark.unit
def test_get_token_unauthorized(test_app, token_non_existing_user):
    response = test_app.post(url='/users/token',
                             data={'username': 'non_existing_user', 'password': 'non_existing_user', 'scope': ''},
                             headers={"content-type": "application/x-www-form-urlencoded"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Incorrect username or password"}


@pytest.mark.unit
def test_get_token(test_app, token_admin):
    response = token_admin
    payload = jwt.decode(response['access_token'], JWT_KEY, algorithms=[ALGORITHM])

    assert payload.get('sub') == 'admin'
    assert payload.get('scopes') == ['USERS:READ', 'USERS:WRITE']


@pytest.mark.unit
def test_extended_token(test_app, token_admin):
    token = token_admin
    data = {"token_user": "admin", "days_valid": 2, "scopes": "USERS:READ"}
    response = test_app.post(url='/users/extendedtoken',
                             data=data,
                             headers={"content-type": "application/x-www-form-urlencoded",
                                      "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 200
    assert "access_token" in response.json().keys()
    assert response.json()["token_type"] == "bearer"


@pytest.mark.unit
def test_extended_token_user_not_found(test_app, token_admin):
    token = token_admin
    data = {"token_user": "user_not_found", "days_valid": 2, "scopes": "USERS:READ"}

    response = test_app.post(url='/users/extendedtoken',
                             data=data,
                             headers={"content-type": "application/x-www-form-urlencoded",
                                      "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 404


@pytest.mark.unit
def test_add_user(test_app, token_admin, scopeless_user_data):
    token = token_admin
    data = scopeless_user_data
    response = test_app.post(url='/users/add',
                             data=json.dumps(data),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == 200
    assert response.json() == "User with username scopeless_user has successfully been added to the DB"


@pytest.mark.unit
def test_add_user_duplicate(test_app, token_admin, scopeless_user_data):
    token = token_admin
    data = scopeless_user_data
    response = test_app.post(url='/users/add',
                             data=json.dumps(data),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == 400
    assert response.json() == {"detail": "A user with username scopeless_user already exists"}
