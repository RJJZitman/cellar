import pytest

from fastapi import status


@pytest.mark.unit
def test_get_owners(test_app, token_new_user, cellar_read_user_data):
    data = cellar_read_user_data
    token = token_new_user(data=data)
    response = test_app.get(url='/cellar/owners/get',
                            headers={"content-type": "application/x-www-form-urlencoded",
                                     "Authorization": f"Bearer {token['access_token']}"})
    del data['password']

    assert response.status_code == status.HTTP_200_OK
    assert data in response.json()

# @pytest.mark.unit
# def test_