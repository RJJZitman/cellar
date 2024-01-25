import pytest

from fastapi import status
from polyfactory.pytest_plugin import register_fixture
from polyfactory.factories.pydantic_factory import ModelFactory

from api.routers import cellar_funcs
from api.models import CellarOutModel, RatingModel


@register_fixture
class RatingModelFactory(ModelFactory[RatingModel]):
    ...


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
def test_get_storage_units(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_x):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    response = test_app.get(url='/cellar_views/storages/get',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})
    storage_unit_data["owner_id"] = user_data["id"]
    storage_unit_data['id'] = get_resp[-1]['id']

    assert response.status_code == status.HTTP_200_OK
    assert storage_unit_data in response.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("your_ratings", [True, False])
async def test_get_wine_rating(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_x,
                               bottle_cellar_fixture, db_monkeypatch, your_ratings):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])

    w_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                            vintage=bottle_info.wine_info.vintage)
    response = test_app.get(url=(f'/cellar_views/wine_in_cellar/get_wine_ratings'
                                 f'?wine_id={w_id}&only_your_ratings={your_ratings}'),
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_wine_rating_no_wine(test_app, token_new_user, cellar_all_user_data):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    response = test_app.get(url=f'/cellar_views/wine_in_cellar/get_wine_ratings?wine_id=9999745&only_your_ratings=True',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_your_ratings(test_app, token_new_user, cellar_all_user_data, db_monkeypatch, new_storage_unit,
                                rating_model_factory: RatingModelFactory, fake_storage_unit_x, bottle_cellar_fixture):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    rating_data = rating_model_factory.build()
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=6, storage_unit=get_resp[-1]['id'])

    wine_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                               vintage=bottle_info.wine_info.vintage)

    await cellar_funcs.add_rating_to_db(db_conn=db_test_conn, user_id=user_data['id'], rating=rating_data,
                                        wine_id=wine_id)
    response = test_app.get(url=f'/cellar_views/wine_in_cellar/get_your_ratings',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})

    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_get_your_bottles_no_storage_unit(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                                fake_storage_unit_x, bottle_cellar_fixture, db_monkeypatch):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    quantity = 6
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=quantity, storage_unit=get_resp[-1]['id'])

    response = test_app.get(url=f'/cellar_views/wine_in_cellar/get_your_bottles',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})

    assert len(response.json()) >= 1
    assert isinstance(response.json(), list)
    assert all(isinstance(CellarOutModel(**entry), CellarOutModel) for entry in response.json())


@pytest.mark.asyncio
async def test_get_your_bottles_storage_unit(test_app, token_new_user, cellar_all_user_data, new_storage_unit,
                                             fake_storage_unit_x):
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)

    response = test_app.get(url=f'/cellar_views/wine_in_cellar/get_your_bottles?storage_unit={get_resp[-1]["id"]}',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})

    assert response.json() == []


@pytest.mark.asyncio
async def test_get_stock_on_bottle(test_app, token_new_user, cellar_all_user_data, new_storage_unit, fake_storage_unit_x,
                                   bottle_cellar_fixture, db_monkeypatch):
    db_test_conn = db_monkeypatch
    user_data = cellar_all_user_data
    token = token_new_user(data=user_data)
    storage_unit_data = fake_storage_unit_x()
    post_resp, get_resp = new_storage_unit(storage_unit_data=storage_unit_data, token=token)
    quantity = 6
    resp, bottle_info = bottle_cellar_fixture(token=token, add=True, quantity=quantity, storage_unit=get_resp[-1]['id'])

    w_id = await cellar_funcs.get_bottle_id(db_conn=db_test_conn, name=bottle_info.wine_info.name,
                                            vintage=bottle_info.wine_info.vintage)
    response = test_app.get(url=f'/cellar_views/wine_in_cellar/get_stock_on_bottle?wine_id={w_id}',
                            headers={"content-type": "application/json",
                                     "Authorization": f"Bearer {token['access_token']}"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]['quantity'] == quantity
