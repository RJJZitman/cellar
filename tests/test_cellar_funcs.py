import pytest

from fastapi import HTTPException, status
from polyfactory.pytest_plugin import register_fixture
from polyfactory.factories.pydantic_factory import ModelFactory
from sqlalchemy.exc import IntegrityError

from api.routers import cellar_funcs
from api.models import GeographicInfoModel, OwnerModel


@register_fixture
class GeographicInfoFactory(ModelFactory[GeographicInfoModel]):
    ...


@pytest.mark.unit
def test_unpack_geo_info(geographic_info_factory: GeographicInfoFactory):
    geographic_info = geographic_info_factory.build()
    unpacked = (f"country: {geographic_info.country},\tregion: {geographic_info.region},"
                f"\tadditional_info: {geographic_info.additional_info}")
    assert cellar_funcs.unpack_geo_info(geographic_info=geographic_info) == unpacked


@pytest.mark.asyncio
async def test_get_storage_id(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_1,
                              db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_1
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    storage_id = await cellar_funcs.get_storage_id(db_conn=db_test_conn, current_user=OwnerModel(**user_data),
                                                   location=storage_unit_data['location'],
                                                   description=storage_unit_data['description'])
    assert storage_id[0] == get_resp[-1]['id']


@pytest.mark.asyncio
async def test_get_storage_id_non_existing(test_app, cellar_all_user_data, new_storage_unit,
                                           fake_storage_unit_non_existing, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    storage_unit_data = fake_storage_unit_non_existing

    with pytest.raises(HTTPException) as exc_info:
        await cellar_funcs.get_storage_id(db_conn=db_test_conn, current_user=OwnerModel(**user_data),
                                          location=storage_unit_data['location'],
                                          description=storage_unit_data['description'])
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_verify_storage_exists(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                     fake_storage_unit_2, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_2
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    assert await cellar_funcs.verify_storage_exists(db_conn=db_test_conn,storage_id=get_resp[0]['id'])


@pytest.mark.asyncio
async def test_verify_storage_exists_non_existing(test_app, cellar_all_user_data, new_storage_unit,
                                                  fake_storage_unit_non_existing, db_monkeypatch):
    db_test_conn = db_monkeypatch
    assert not await cellar_funcs.verify_storage_exists(db_conn=db_test_conn,storage_id=10**6)


@pytest.mark.asyncio
async def test_verify_empty_storage_unit(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                         fake_storage_unit_3, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_3
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    assert await cellar_funcs.verify_empty_storage_unit(db_conn=db_test_conn,storage_id=get_resp[-1]['id'])


@pytest.mark.asyncio
async def test_verify_empty_storage_unit_not_empty(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                                   fake_storage_unit_4, bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_4
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])

    with pytest.raises(HTTPException) as exc_info:
        await cellar_funcs.verify_empty_storage_unit(db_conn=db_test_conn,storage_id=get_resp[-1]['id'])
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_verify_wine_in_db(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_9,
                                 bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_9
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # add bottle
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])
    assert await cellar_funcs.verify_wine_in_db(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                                vintage=bottle_info.wine_info.vintage)


@pytest.mark.asyncio
async def test_verify_wine_in_db_not(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    assert not await cellar_funcs.verify_wine_in_db(db_conn=db_test_conn, name="no_wine", vintage=1111)


@pytest.mark.asyncio
async def test_get_bottle_id(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_10,
                             bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_10
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # add bottle
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])
    assert await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                            vintage=bottle_info.wine_info.vintage)


@pytest.mark.asyncio
async def test_get_bottle_id_non_existing(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    with pytest.raises(HTTPException) as exc_info:
        await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name="not_exist", vintage=2024)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_verify_bottle_exists_in_storage_unit(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                                    fake_storage_unit_11, bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_11
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # add bottle
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)

    assert await cellar_funcs.verify_bottle_exists_in_storage_unit(db_conn=db_test_conn, wine_id=wine_id,
                                                                   storage_unit=get_resp[-1]['id'],
                                                                   bottle_size=bottle_info.bottle_size_cl)


@pytest.mark.asyncio
async def test_verify_bottle_exists_in_storage_unit_not(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    assert not await cellar_funcs.verify_bottle_exists_in_storage_unit(db_conn=db_test_conn, wine_id=9999,
                                                                       storage_unit=999,
                                                                       bottle_size=99999)


@pytest.mark.asyncio
async def test_update_quantity_in_cellar(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                         fake_storage_unit_12, bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_12
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # add bottle
    quantity = 6
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=quantity, storage_unit=get_resp[-1]['id'])
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)

    # remove all bottles but one
    query = ("SELECT * FROM cellar.cellar "
             "WHERE wine_id = %(wine_id)s "
             "AND storage_unit = %(storage_unit)s "
             "AND bottle_size_cl = %(bottle_size_cl)s")
    params = {"quantity": str(bottle_info.quantity),
              "wine_id": str(wine_id),
              "storage_unit": str(bottle_info.storage_unit),
              "bottle_size_cl": str(bottle_info.bottle_size_cl)}
    bottle_info.quantity = quantity - 1
    await cellar_funcs.update_quantity_in_cellar(db_conn=db_test_conn, wine_id=wine_id, bottle_data=bottle_info,
                                                 add=False)
    bottles_left = db_test_conn.execute_query_select(query=query, params=params, get_fields=True)
    assert bottles_left[0]['quantity'] == 1

    # remove last bottle
    bottle_info.quantity = 1
    await cellar_funcs.update_quantity_in_cellar(db_conn=db_test_conn, wine_id=wine_id, bottle_data=bottle_info,
                                                 add=False)
    bottles_left = db_test_conn.execute_query_select(query=query, params=params, get_fields=True)
    assert not len(bottles_left)


@pytest.mark.asyncio
async def test_update_quantity_in_cellar_not(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                             fake_storage_unit_13, bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_13
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # add bottle
    quantity = 6
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=quantity, storage_unit=get_resp[-1]['id'])
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)

    # remove more bottles than possible
    bottle_info.quantity = quantity + 1
    with pytest.raises(HTTPException) as exc_info:
        await cellar_funcs.update_quantity_in_cellar(db_conn=db_test_conn, wine_id=wine_id, bottle_data=bottle_info,
                                                     add=False)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_add_bottle_to_cellar(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                    fake_storage_unit_14, bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_14
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    # add bottle
    quantity = 6
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=quantity, storage_unit=get_resp[-1]['id'])
    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)

    await cellar_funcs.add_bottle_to_cellar(db_conn=db_test_conn, wine_id=wine_id, owner_id=user_data['id'],
                                            wine_data=bottle_info)
    wine_in_cellar_data = db_test_conn.execute_query_select(query=("SELECT * FROM cellar.cellar "
                                                                   "WHERE wine_id = %(wine_id)s "
                                                                   "AND storage_unit = %(storage_unit)s "
                                                                   "AND bottle_size_cl = %(bottle_size_cl)s"),
                                                            params={"quantity": str(bottle_info.quantity),
                                                                    "wine_id": str(wine_id),
                                                                    "storage_unit": str(bottle_info.storage_unit),
                                                                    "bottle_size_cl": str(bottle_info.bottle_size_cl)},
                                                            get_fields=True)
    assert wine_in_cellar_data[0]['quantity'] == quantity * 2


