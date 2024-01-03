import json

import pytest

from fastapi import status


@pytest.mark.unit
def test_get_owners(test_app, token_new_user, cellar_read_user_data):
    data = cellar_read_user_data
    token = token_new_user(data=data)
    # add a user and verify if you can find it
    response = test_app.get(url='/cellar/owners/get',
                            headers={"content-type": "application/x-www-form-urlencoded",
                                     "Authorization": f"Bearer {token['access_token']}"})
    del data['password']

    assert response.status_code == status.HTTP_200_OK
    assert data in response.json()


@pytest.mark.unit
def test_post_storage_unit(test_app, token_new_user, cellar_all_user_data):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = {"location": "fake_storage", "description": "fake_storage_description"}
    # add a storage unit
    response = test_app.post(url='/cellar/storages/add',
                             data=json.dumps(storage_unit_data),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == "Storage unit has successfully been added to the DB"


@pytest.mark.unit
def test_get_storage_units(test_app, token_new_user, cellar_all_user_data):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = {"location": "fake_storage", "description": "fake_storage_description"}
    # add a storage unit and verify if you can find it
    test_app.post(url='/cellar/storages/add',
                  data=json.dumps(storage_unit_data),
                  headers={"content-type": "application/json",
                           "Authorization": f"Bearer {token['access_token']}"})
    response = test_app.get(url='/cellar/storages/get',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})
    storage_unit_data["id"] = None

    assert response.status_code == status.HTTP_200_OK
    assert storage_unit_data in response.json()


@pytest.mark.unit
def test_delete_storage_units(test_app, token_new_user, cellar_all_user_data):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = {"location": "del_fake_storage", "description": "del_fake_storage_description"}
    # add a storage unit and collect all units
    test_app.post(url='/cellar/storages/add',
                  data=json.dumps(storage_unit_data),
                  headers={"content-type": "application/json",
                           "Authorization": f"Bearer {token['access_token']}"})
    storages_pre = test_app.get(url='/cellar/storages/get',
                                headers={"content-type": "application/json",
                                         "Authorization": f"Bearer {token['access_token']}"})
    print("Database state before deletion:", storages_pre.json())

    # delete the storage unit and verify that it is gone from the DB
    response = test_app.delete(url='/cellar/storages/delete',
                               params=storage_unit_data,
                               headers={"content-type": "application/json",
                                        "Authorization": f"Bearer {token['access_token']}"})

    storages_post = test_app.get(url='/cellar/storages/get',
                                 headers={"content-type": "application/json",
                                         "Authorization": f"Bearer {token['access_token']}"})
    storage_unit_data["id"] = None
    print("Response status code:", response.status_code)
    print("Response content:", response.json())
    assert storages_post.status_code == status.HTTP_200_OK
    assert storage_unit_data not in storages_post.json()
    assert storage_unit_data in storages_pre.json()
