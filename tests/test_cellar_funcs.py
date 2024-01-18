import pytest

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
    assert storage_id[0] == get_resp[0]['id']

# @pytest.mark.unit
# def test_get_storage_id_non_existing(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
#                                      fake_storage_unit_1, db_monkeypatch):
#     db_test_conn = db_monkeypatch
#     user_data = cellar_all_user_data
#     token = token_new_user(data=user_data)
#     storage_unit_data = fake_storage_unit_1
#     new_storage_unit(storage_unit_data=storage_unit_data, token=token)
#
#     storage_id = cellar_funcs.get_storage_id(db_conn=db_test_conn, current_user=OwnerModel(**user_data),
#                                              location=storage_unit_data['location'],
#                                              description=storage_unit_data['description'])
#     assert storage_id

