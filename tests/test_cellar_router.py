import pytest

from fastapi import status


@pytest.mark.unit
def test_get_owners(test_app, token_cellar_read):
    data = {'id': 5,
            'name': 'cellar',
            'username': 'cellar',
            'password': 'cellar',
            'scopes': 'CELLAR:READ',
            'is_admin': 0,
            'enabled': 1}
    token = token_cellar_read(data=data)
    response = test_app.get(url='/cellar/owners/get',
                            headers={"content-type": "application/x-www-form-urlencoded",
                                     "Authorization": f"Bearer {token['access_token']}"})
    del data['password']
    assert response.status_code == status.HTTP_200_OK
    assert data in response.json()

# @pytest.mark.unit
# def test_