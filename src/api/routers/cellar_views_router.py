from typing import Annotated
from datetime import datetime

from fastapi import HTTPException, status
from fastapi import APIRouter, Depends, Security

from db.jdbc_interface import JdbcDbConn

from .cellar_funcs import wine_in_db, get_cellar_out_data
from ..constants import DB_CONN
from ..authentication import get_current_active_user
from ..models import OwnerModel, StorageOutModel, RatingInDbModel, CellarOutModel


router = APIRouter(prefix="/cellar_views",
                   tags=["cellar_views"],
                   dependencies=[Security(get_current_active_user, scopes=['CELLAR:READ'])],
                   responses={404: {"description": "Not Found"}})


@router.get("/owners/get_your_id", dependencies=[Security(get_current_active_user)])
async def get_owners(current_user: Annotated[OwnerModel, Depends(get_current_active_user)]) -> int:
    """
    Retrieve your ID.

    Required scope(s): CELLAR:READ
    """
    return current_user.id


@router.get("/storages/get", response_model=list[StorageOutModel], dependencies=[Security(get_current_active_user)])
async def get_storage_units(db_conn: Annotated[JdbcDbConn, Depends(DB_CONN)],
                            current_user: Annotated[OwnerModel, Depends(get_current_active_user)]
                            ) -> list[StorageOutModel]:
    """
    Retrieve all your storage units registered within the DB.

    Required scope(s): CELLAR:READ
    """
    return db_conn.execute_query_select(query="SELECT * FROM cellar.storages WHERE owner_id = %(owner_id)s",
                                        params={"owner_id": current_user.id},
                                        get_fields=True)


@router.get("/wine_in_cellar/get_wine_ratings", response_model=list[RatingInDbModel],
            dependencies=[Security(get_current_active_user)])
async def get_wine_rating(db_conn: Annotated[JdbcDbConn, Depends(DB_CONN)],
                          current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                          wine_id: int,
                          only_your_ratings: bool = True) -> list[RatingInDbModel]:
    """
    Retrieves ratings for a specific wine/bottle. Make sure to set the 'only_your_ratings' to True if you only want
    to see your ratings on the wine. If set to False, all ratings will be given.

    Required scope(s): CELLAR:READ
    """
    # Verify the wine exists in the DB
    if not await wine_in_db(db_conn=db_conn, wine_id=wine_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Wine with wine_id: {wine_id} is not found in the DB. Make sure to use an "
                                   f"existing wine ID in order to rate the correct wine")
    # Retrieve the ratings from the DB
    query = "SELECT * FROM cellar.ratings WHERE wine_id = %(wine_id)s"
    if only_your_ratings:
        # Note that an f-string is used for the rater_id since sql-injection risks are mitigated due to the user id
        # originating from the OwnerModel and thus enforcing the value to be an integer
        query = f"{query} AND rater_id = '{current_user.id}'"
    return db_conn.execute_query_select(query=query, params={"wine_id": wine_id}, get_fields=True)


@router.get("/wine_in_cellar/get_your_ratings", response_model=list[RatingInDbModel],
            dependencies=[Security(get_current_active_user)])
async def get_your_ratings(db_conn: Annotated[JdbcDbConn, Depends(DB_CONN)],
                           current_user: Annotated[OwnerModel, Depends(get_current_active_user)]
                           ) -> list[RatingInDbModel]:
    """
    Retrieves all your ratings for all wines/bottles.

    Required scope(s): CELLAR:READ
    """
    # Retrieve the ratings from the DB
    return db_conn.execute_query_select(query="SELECT * FROM cellar.ratings WHERE rater_id = %(rater_id)s",
                                        params={"rater_id": current_user.id}, get_fields=True)


@router.get("/wine_in_cellar/get_your_bottles", response_model=list[CellarOutModel],
            dependencies=[Security(get_current_active_user)])
async def get_your_bottles(db_conn: Annotated[JdbcDbConn, Depends(DB_CONN)],
                           current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                           storage_unit: int | None = None) -> list[CellarOutModel]:
    """
    Get an overview of all your bottles stored in your cellar. If the 'storage_unit' id is specified, only the bottles
    in that specific storage unit are shown.

    Required scope(s): CELLAR:READ
    """
    if storage_unit is None:
        return get_cellar_out_data(db_conn=db_conn, params={"user_id": current_user.id},
                                   where="WHERE c.owner_id = %(user_id)s")
    else:
        return get_cellar_out_data(db_conn=db_conn, params={"user_id": current_user.id, "storage_unit": storage_unit},
                                   where="WHERE c.owner_id = %(user_id)s AND storage_unit = %(storage_unit)s")


@router.get("/wine_in_cellar/get_stock_on_bottle",  response_model=list[CellarOutModel],
            dependencies=[Security(get_current_active_user)])
async def get_stock_on_bottle(db_conn: Annotated[JdbcDbConn, Depends(DB_CONN)],
                              current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                              wine_id: int) -> list[CellarOutModel]:
    """
    Get an overview of all your bottles of a specific wine stored in your cellar.

    Required scope(s): CELLAR:READ
    """
    return get_cellar_out_data(db_conn=db_conn, params={"user_id": current_user.id, "wine_id": wine_id},
                               where="WHERE c.owner_id = %(user_id)s AND wine_id = %(wine_id)s")


@router.get("/wine_in_cellar/drink_in_window", response_model=list[CellarOutModel],
            dependencies=[Security(get_current_active_user)])
async def get_bottle_open_window(db_conn: Annotated[JdbcDbConn, Depends(DB_CONN)],
                                 current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                                 drink_year: int | None = None,
                                 beverage_type: str | None = None) -> list[CellarOutModel]:
    """
    Retrieve all bottles that are drinkable now or within a specified year. The returned list of drink-ready bottles
    can be trimmed by specifying a certain beverage_type.

    Required scope(s): CELLAR:READ
    """
    drink_when_cond = 'c.drink_from <= %(drink_year)s AND c.drink_before >= %(drink_year)s'
    owner_cond = 'c.owner_id = %(user_id)s'
    drink_year = datetime.now().year if drink_year is None else drink_year

    params = {"drink_year": datetime(year=drink_year, month=1, day=1), "user_id": current_user.id}
    where = f'WHERE {drink_when_cond} AND {owner_cond} '
    if beverage_type is not None:
        params["bev_type"] = beverage_type
        where += f'AND w.type = %(bev_type)s'
    return get_cellar_out_data(db_conn=db_conn, params=params, where=where)
