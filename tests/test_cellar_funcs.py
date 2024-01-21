import pytest

from fastapi import HTTPException, status
from polyfactory.pytest_plugin import register_fixture
from polyfactory.factories.pydantic_factory import ModelFactory

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
