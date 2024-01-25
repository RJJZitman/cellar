import json

import pytest

from fastapi import status
from polyfactory.pytest_plugin import register_fixture
from polyfactory.factories.pydantic_factory import ModelFactory

from api.routers import cellar_funcs
from api.models import CellarInModel, RatingInDbModel, ConsumedBottleModel


@register_fixture
class CellarInModelFactory(ModelFactory[CellarInModel]):
    ...


@register_fixture
class RatingInDbModelFactory(ModelFactory[RatingInDbModel]):
    ...


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


@pytest.mark.unit
def test_add_wine_to_cellar_no_storage(test_app, token_new_user, cellar_all_user_data,
                                       cellar_in_model_factory: CellarInModelFactory):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    wine_data = cellar_in_model_factory.build().dict()
    wine_data['storage_unit'] = 10**9

    response = test_app.post(url='/cellar/wine_in_cellar/add',
                             data=json.dumps(wine_data, default=str),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_wine_to_cellar(test_app, token_new_user, cellar_all_user_data, new_storage_unit, db_monkeypatch,
                                  fake_storage_unit_x, cellar_in_model_factory: CellarInModelFactory):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    wine_data = cellar_in_model_factory.build()
    wine_data.storage_unit = get_resp[0]['id']

    # assert new bottle has successful call
    response = test_app.post(url='/cellar/wine_in_cellar/add',
                             data=json.dumps(wine_data.dict(), default=str),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})
    response2 = test_app.post(url='/cellar/wine_in_cellar/add',
                              data=json.dumps(wine_data.dict(), default=str),
                              headers={"content-type": "application/json",
                                       "Authorization": f"Bearer {token['access_token']}"})
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=wine_data.wine_info.name,
                                               vintage=wine_data.wine_info.vintage)
    bottle_data = db_test_conn.execute_query_select(query=("SELECT * FROM cellar.cellar "
                                                           "WHERE wine_id = %(wine_id)s "
                                                           "AND storage_unit = %(storage_unit)s"),
                                                    params={"wine_id": wine_id,
                                                            "storage_unit": wine_data.storage_unit},
                                                    get_fields=True)
    assert bottle_data[0]['quantity'] == wine_data.quantity * 2
    assert response.json() == "Bottle has successfully been added to the DB"
    assert response2.json() == "Bottle has successfully been added to the DB"


@pytest.mark.asyncio
async def test_add_a_rating_wine_not_exist(test_app, token_new_user, cellar_all_user_data,
                                           rating_in_db_model_factory: RatingInDbModelFactory):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    rating_data = rating_in_db_model_factory.build()

    # assert a rating for a wine that does not exist in the DB cannot be processed
    response = test_app.post(url='/cellar/wine_in_cellar/add_rating?wine_id=10967393',
                             data=json.dumps(rating_data.dict(), default=str),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_a_rating(test_app, token_new_user, cellar_all_user_data, new_storage_unit, db_monkeypatch,
                            fake_storage_unit_x, rating_in_db_model_factory: RatingInDbModelFactory,
                            cellar_in_model_factory: CellarInModelFactory):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    wine_data = cellar_in_model_factory.build()
    rating_data = rating_in_db_model_factory.build()

    wine_data.storage_unit = get_resp[0]['id']
    # add new bottle and therefore wine to the DB
    _ = test_app.post(url='/cellar/wine_in_cellar/add',
                      data=json.dumps(wine_data.dict(), default=str),
                      headers={"content-type": "application/json",
                               "Authorization": f"Bearer {token['access_token']}"})
    # extract the auto incremented id of the wine that's just been added
    wine_id = db_test_conn.execute_query_select(query=("SELECT * FROM cellar.wines "
                                                       "WHERE name = %(name)s "
                                                       "AND vintage = %(vintage)s"),
                                                params={"name": wine_data.wine_info.name,
                                                        "vintage": wine_data.wine_info.vintage},
                                                get_fields=True)[0]['id']
    response = test_app.post(url=f'/cellar/wine_in_cellar/add_rating?wine_id={wine_id}',
                             data=json.dumps(rating_data.dict(), default=str),
                             headers={"content-type": "application/json",
                                      "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 200
    assert response.json() == "Rating has successfully been added to the DB"


@pytest.mark.asyncio
async def test_remove_consumed_from_stock(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                          fake_storage_unit_x, bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # add bottle
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)
    # bottle_info.wine_id = wine_id
    consumed_bottle_info = {"bottle_data": {"wine_id": wine_id, "storage_unit": bottle_info.storage_unit,
                                            "bottle_size_cl": bottle_info.bottle_size_cl,
                                            "quantity": bottle_info.quantity},
                            "rating": None}
    response = test_app.patch(url='/cellar/wine_in_cellar/consumed?rate_bottle=false',
                              data=json.dumps(consumed_bottle_info, default=str),
                              headers={"content-type": "application/json",
                                       "Authorization": f"Bearer {token['access_token']}"})

    assert response.json() == "Consumed bottle is updated in the DB"


@pytest.mark.asyncio
async def test_remove_consumed_from_stock_rating(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                                 fake_storage_unit_x, bottle_cellar_fixture, db_monkeypatch,
                                                 rating_in_db_model_factory: RatingInDbModelFactory):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    rating_data = rating_in_db_model_factory.build()

    # add bottle
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)
    # bottle_info.wine_id = wine_id
    consumed_bottle_info = {"bottle_data": {"wine_id": wine_id, "storage_unit": bottle_info.storage_unit,
                                            "bottle_size_cl": bottle_info.bottle_size_cl,
                                            "quantity": bottle_info.quantity},
                            "rating": rating_data.dict()}
    response = test_app.patch(url='/cellar/wine_in_cellar/consumed?rate_bottle=true',
                              data=json.dumps(consumed_bottle_info, default=str),
                              headers={"content-type": "application/json",
                                       "Authorization": f"Bearer {token['access_token']}"})

    assert response.json() == "Consumed bottle is updated in the DB"


@pytest.mark.asyncio
async def test_remove_consumed_unknown_bottle(test_app, token_new_user, cellar_all_user_data):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    consumed_bottle_info = {"bottle_data": {"wine_id": 109084874, "storage_unit": 5,
                                            "bottle_size_cl": 5,
                                            "quantity": 5},
                            "rating": None}
    response = test_app.patch(url='/cellar/wine_in_cellar/consumed?rate_bottle=false',
                              data=json.dumps(consumed_bottle_info, default=str),
                              headers={"content-type": "application/json",
                                       "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_move_bottle_to_other_storage(test_app, token_new_user, cellar_all_user_data):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    response = test_app.patch(url='/cellar/wine_in_cellar/move?cellar_id=2&new_storage_unit=994534599',
                              headers={"content-type": "application/json",
                                       "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_move_bottle_to_other_storage(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                            fake_storage_unit_x, bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])

    storage_unit = get_resp[-1]['id']
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)
    cellar_id = cellar_funcs.get_cellar_out_data(db_conn=db_test_conn,
                                                 where="WHERE wine_id = %(wine_id)s",
                                                 params={"wine_id": wine_id})[0]['cellar_id']
    response = test_app.patch(url=f'/cellar/wine_in_cellar/move?cellar_id={cellar_id}&new_storage_unit={storage_unit}',
                              headers={"content-type": "application/json",
                                       "Authorization": f"Bearer {token['access_token']}"})
    assert response.json() == f"Bottle has successfully been transferred to storage unit {storage_unit}"


@pytest.mark.asyncio
async def test_move_bottle_to_other_storage_no_storage(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                                       fake_storage_unit_x, bottle_cellar_fixture):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])

    storage_unit = get_resp[-1]['id']
    response = test_app.patch(url=f'/cellar/wine_in_cellar/move?cellar_id=1&new_storage_unit={storage_unit+1}',
                              headers={"content-type": "application/json",
                                       "Authorization": f"Bearer {token['access_token']}"})
    assert response.status_code == 404
