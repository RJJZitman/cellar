import json

import pytest

from fastapi import status


@pytest.mark.unit
def test_get_owners(test_app, token_new_user, cellar_read_user_data):
    data = cellar_read_user_data
    token = token_new_user(data=data)
    # add a user and verify if you can find it
    response = test_app.get(url='/cellar_views/owners/get',
                            headers={"content-type": "application/x-www-form-urlencoded",
                                     "Authorization": f"Bearer {token['access_token']}"})
    del data['password']

    assert response.status_code == status.HTTP_200_OK
    assert data in response.json()


@pytest.mark.unit
def test_get_storage_units(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_8):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_8
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    response = test_app.get(url='/cellar_views/storages/get',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})
    storage_unit_data["owner_id"] = user_data["id"]
    storage_unit_data['id'] = get_resp[-1]['id']

    assert response.status_code == status.HTTP_200_OK
    assert storage_unit_data in response.json()

