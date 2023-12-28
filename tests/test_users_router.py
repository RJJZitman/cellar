import pytest

import jwt

from fastapi import status

from api.constants import JWT_KEY, ALGORITHM


@pytest.mark.unit
def test_get_token_unauthorized(test_app):
    response = test_app.post(url='/users/token',
                             data={'username': 'not_a_user', 'password': 'not_a_user', 'scope': 'users:read'},
                             headers={"content-type": "application/x-www-form-urlencoded"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.text == '{"detail":"Incorrect username or password"}'


@pytest.mark.unit
def test_get_token(test_app, token_admin):
    response = token_admin
    payload = jwt.decode(response['access_token'], JWT_KEY, algorithms=[ALGORITHM])

    assert payload.get('sub') == 'admin'
    assert payload.get('scopes') == ['USERS:READ']
