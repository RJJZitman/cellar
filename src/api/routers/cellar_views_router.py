from typing import Annotated

from fastapi import HTTPException, status
from fastapi import APIRouter, Depends, Security

from .cellar_funcs import wine_in_db, get_cellar_out_data

from ..db_utils import MariaDB
from ..constants import DB_CONN
from ..authentication import get_current_active_user
from ..models import OwnerModel, StorageOutModel, RatingInDbModel, CellarOutModel


router = APIRouter(prefix="/cellar_views",
                   tags=["cellar_views"],
                   dependencies=[Security(get_current_active_user, scopes=['CELLAR:READ'])],
                   responses={404: {"description": "Not Found"}})


@router.get("/owners/get", response_model=list[OwnerModel], dependencies=[Security(get_current_active_user)])
async def get_owners(db_conn: Annotated[MariaDB, Depends(DB_CONN)]) -> list[OwnerModel]:
    """
    Retrieve all registered wine/beer owners.
    Required scope(s): CELLAR:READ
    """
    return db_conn.execute_query_select(query="SELECT * FROM cellar.owners", get_fields=True)


@router.get("/storages/get", response_model=list[StorageOutModel], dependencies=[Security(get_current_active_user)])
async def get_storage_units(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                            current_user: Annotated[OwnerModel, Depends(get_current_active_user)]
                            ) -> list[StorageOutModel]:
    """
    Retrieve all owners registered within the DB.
    Required scope(s): CELLAR:READ
    """
    return db_conn.execute_query_select(query="SELECT * FROM cellar.storages WHERE owner_id = %(owner_id)s",
                                        params={"owner_id": current_user.id},
                                        get_fields=True)


@router.get("/wine_in_cellar/get_wine_ratings", response_model=list[RatingInDbModel],
            dependencies=[Security(get_current_active_user)])
async def get_wine_rating(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                          current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                          wine_id: int,
                          only_your_ratings: bool = True) -> list[RatingInDbModel]:
    """
    Retrieves ratings for a specific wine/bottle. Make sure to set the 'only_your_ratings' to True if you only want
    to see your ratings on the wine. If set to False, all ratings will be given.
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
async def get_your_ratings(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                           current_user: Annotated[OwnerModel, Depends(get_current_active_user)]
                           ) -> list[RatingInDbModel]:
    """
    Retrieves all your ratings for all wines/bottles.
    """
    # Retrieve the ratings from the DB
    return db_conn.execute_query_select(query="SELECT * FROM cellar.ratings WHERE rater_id = %(rater_id)s",
                                        params={"rater_id": current_user.id}, get_fields=True)


@router.get("/wine_in_cellar/get_your_bottles", response_model=list[CellarOutModel],
            dependencies=[Security(get_current_active_user)])
async def get_your_bottles(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                           current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                           storage_unit: int | None = None) -> list[CellarOutModel]:
    """
    Get an overview of all your bottles stored in your cellar. If the 'storage_unit' id is specified, only the bottles
    in that specific storage unit are shown.
    """
    if storage_unit is None:
        return get_cellar_out_data(db_conn=db_conn, params={"user_id": current_user.id},
                                   where="WHERE c.owner_id = %(user_id)s")
    else:
        return get_cellar_out_data(db_conn=db_conn, params={"user_id": current_user.id, "storage_unit": storage_unit},
                                   where="WHERE c.owner_id = %(user_id)s AND storage_unit = %(storage_unit)s")


@router.get("/wine_in_cellar/get_stock_on_bottle",  response_model=list[CellarOutModel],
            dependencies=[Security(get_current_active_user)])
async def get_stock_on_bottle(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                              current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                              wine_id: int) -> list[CellarOutModel]:
    """
    Get an overview of all your bottles of a specific bottle stored in your cellar.
    """
    return get_cellar_out_data(db_conn=db_conn, params={"user_id": current_user.id, "wine_id": wine_id},
                               where="WHERE c.owner_id = %(user_id)s AND wine_id = %(wine_id)s")

