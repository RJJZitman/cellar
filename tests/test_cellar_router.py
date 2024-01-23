import json

import pytest

from fastapi import status


@pytest.mark.unit
def test_post_storage_unit(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_x):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    # add a storage unit
    response = test_app.post(url='/cellar/storages/add',
                             data=json.dumps(storage_unit_data),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == "Storage unit has successfully been added to the DB"


@pytest.mark.unit
def test_delete_storage_units(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_x):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # delete the storage unit and verify that it is gone from the DB
    response = test_app.delete(url='/cellar/storages/delete',
                               params=storage_unit_data,
                               headers={"content-type": "application/json",
                                        "Authorization": f"Bearer {token['access_token']}"})

    storages_post = test_app.get(url='/cellar_views/storages/get',
                                 headers={"content-type": "application/json",
                                          "Authorization": f"Bearer {token['access_token']}"})
    storage_unit_data["owner_id"] = user_data["id"]
    storage_unit_data['id'] = get_resp[-1]['id']

    assert response.status_code == status.HTTP_200_OK
    assert storage_unit_data not in storages_post.json()
    assert storage_unit_data in get_resp
