import sys

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
    print(response)
    payload = jwt.decode(response['access_token'], JWT_KEY, algorithms=[ALGORITHM])

    assert payload.get('sub') == 'admin'
    assert payload.get('scopes') == ['USERS:READ']
