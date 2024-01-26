import json

import jwt
import pytest

from fastapi import status

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


@pytest.mark.unit
def test_get_users(test_app, token_new_user, cellar_read_user_data):
    user_data = cellar_read_user_data
    token, user_id = token_new_user(data=user_data)
    response = test_app.get(url='/users/get_users',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})
    # extract the newest user from DB and harmonize vals with raw data
    new_user_data = response.json()[-1]
    del new_user_data['id']
    del user_data['password']
    new_user_data['is_admin'] = 0 if not new_user_data['is_admin'] else 1
    new_user_data['enabled'] = 0 if not new_user_data['enabled'] else 1
    assert response.status_code == status.HTTP_200_OK
    assert user_data == new_user_data


@pytest.mark.unit
def test_delete_users(test_app, token_new_user, expendable_user_data, token_admin):
    user_data = expendable_user_data
    token, user_id = token_new_user(data=user_data)
    admin_token = token_admin
    response_del = test_app.delete(url=f'/users/delete?delete_username={user_data["username"]}',
                                   headers={"content-type": "application/json",
                                            "Authorization": f"Bearer {admin_token['access_token']}"})

    response_get = test_app.get(url='/users/get_users',
                                headers={"content-type": "application/json",
                                         "Authorization": f"Bearer {admin_token['access_token']}"})
    assert response_del.status_code == status.HTTP_200_OK
    assert not sum([1 for user in response_get.json() if user['username'] == user_data['username']])


@pytest.mark.unit
def test_delete_users_not_exist(test_app, token_new_user, expendable_user_data, token_admin):
    user_data = expendable_user_data
    admin_token = token_admin
    response_del = test_app.delete(url=f'/users/delete?delete_username={user_data["username"]}',
                                   headers={"content-type": "application/json",
                                            "Authorization": f"Bearer {admin_token['access_token']}"})
    assert response_del.status_code == status.HTTP_400_BAD_REQUEST
    assert response_del.json()['detail'] == f"No users with username {user_data['username']} exist"


@pytest.mark.unit
def test_update_user_duplicate_new_username(test_app, token_admin, token_new_user, expendable_user_data,
                                            cellar_read_user_data):
    admin_token = token_admin
    cellar_user_data = cellar_read_user_data
    cellar_token, cellar_user_id = token_new_user(data=cellar_user_data)

    ex_user_data = expendable_user_data
    ex_token, ex_user_id = token_new_user(data=ex_user_data)
    current_ex_user_username = ex_user_data['username']
    ex_user_data['username'] = cellar_user_data['username']

    response_upd = test_app.patch(url=f'/users/update?current_username={current_ex_user_username}',
                                  data=json.dumps(ex_user_data),
                                  headers={"content-type": "application/json",
                                           "Authorization": f"Bearer {admin_token['access_token']}"})
    assert response_upd.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.unit
def test_update_user(test_app, token_admin, token_new_user, expendable_user_data, update_user_data):
    admin_token = token_admin

    new_data = update_user_data
    ex_user_data = expendable_user_data
    _, _ = token_new_user(data=ex_user_data)

    response_upd = test_app.patch(url=f'/users/update?current_username={ex_user_data["username"]}',
                                  data=json.dumps(new_data),
                                  headers={"content-type": "application/json",
                                           "Authorization": f"Bearer {admin_token['access_token']}"})
    assert response_upd.status_code == status.HTTP_200_OK
    assert response_upd.json() == "User information updated successfully."

