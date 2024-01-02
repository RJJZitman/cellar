import sys

import pytest


sys.path.append('./src/')
from api.constants import JWT_KEY, ALGORITHM


@pytest.mark.unit
def test_get_owners(test_app, new_user, token_cellar_read):
    data = {'id': 5,
            'name': 'cellar',
            'username': 'cellar',
            'password': 'cellar',
            'scopes': 'CELLAR:READ',
            'is_admin': 0,
            'enabled': 1}
    new_user(data=data)
    token = token_cellar_read(data=data)
    print(token)
    response = test_app.post(url='/cellar/owners/get',
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})
                            # headers={"content-type": "application/x-www-form-urlencoded",
    # assert response.status_code == status.HTTP_200_OK
    assert response.text == '{"detail":"Incorrect username or password"}'

# @pytest.mark.unit
# def test_