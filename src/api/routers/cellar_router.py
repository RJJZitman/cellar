from typing import Annotated

from fastapi import HTTPException, status
from fastapi import APIRouter, Depends, Security, Query

from .cellar_funcs import (get_storage_id, verify_storage_exists, verify_empty_storage_unit, verify_wine_in_db,
                           add_wine_to_db, get_bottle_id, add_bottle_to_cellar, wine_in_db, rating_in_db,
                           add_rating_to_db, update_quantity_in_cellar)

from ..db_utils import MariaDB
from ..constants import DB_CONN
from ..authentication import get_current_active_user
from ..models import (OwnerModel, StorageInModel, StorageOutModel, CellarInModel, RatingModel, RatingInDbModel,
                      ConsumedBottleModel)


router = APIRouter(prefix="/cellar",
                   tags=["cellar"],
                   dependencies=[Security(get_current_active_user, scopes=['CELLAR:READ'])],
                   responses={404: {"description": "Not Found"}})


@router.get("/owners/get", response_model=list[OwnerModel], dependencies=[Security(get_current_active_user)])
async def get_owners(db_conn: Annotated[MariaDB, Depends(DB_CONN)]):
    """
    Retrieve all registered wine/beer owners.
    Required scope(s): CELLAR:READ
    """
    return db_conn.execute_query_select(query="SELECT * FROM cellar.owners", get_fields=True)


@router.get("/storages/get", response_model=list[StorageOutModel], dependencies=[Security(get_current_active_user)])
async def get_storage_units(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                            current_user: Annotated[OwnerModel, Depends(get_current_active_user)]):
    """
    Retrieve all owners registered within the DB.
    Required scope(s): CELLAR:READ
    """
    return db_conn.execute_query_select(query="SELECT * FROM cellar.storages WHERE owner_id = %(owner_id)s",
                                        params={"owner_id": current_user.id},
                                        get_fields=True)


@router.post("/storages/add", dependencies=[Security(get_current_active_user, scopes=['CELLAR:WRITE'])])
async def post_storage_unit(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                            current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                            storage_data: StorageInModel) -> str:
    """
    Add a storage unit to the DB.
    Required scope(s): CELLAR:READ, CELLAR:WRITE
    """
    db_conn.execute_query(query="INSERT INTO cellar.storages (owner_id, location, description) "
                                "VALUES (%(owner_id)s, %(location)s, %(description)s)",
                          params={"owner_id": current_user.id, "location": storage_data.location,
                                  "description": storage_data.description})

    return "Storage unit has successfully been added to the DB"


@router.delete("/storages/delete", dependencies=[Security(get_current_active_user, scopes=['CELLAR:WRITE'])])
async def delete_storage_unit(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                              current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                              location: Annotated[str, Query(max_length=200)],
                              description: Annotated[str, Query(max_length=200)]) -> str:
    """
    Delete a storage unit to the DB. Provide the location and description of the storage unit to select which unit
    should be deleted. Make sure that the storage unit is empty whenever you want to remove it.

    Required scope(s): CELLAR:READ, CELLAR:WRITE
    """
    # Verify empty storage unit
    storage_id = await get_storage_id(db_conn=db_conn, current_user=current_user,
                                      location=location, description=description)

    # Remove the storage unit from DB if it is empty.
    # Note that `verify_empty_storage_unit` raises and error if the storage unit is not empty
    if await verify_empty_storage_unit(db_conn=db_conn, storage_id=storage_id):
        db_conn.execute_query(query="DELETE FROM cellar.storages "
                                    "WHERE location = %(location)s "
                                    "  AND description = %(description)s "
                                    "  AND owner_id = %(owner_id)s",
                              params={"location": location, "description": description, "owner_id": current_user.id})

    return "Storage unit has successfully been removed from the DB"


@router.post("/wine_in_cellar/add", dependencies=[Security(get_current_active_user)])
async def add_wine_to_cellar(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                             current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                             wine_data: CellarInModel):
    """
    Adds bottles to your cellar. Make sure to provide the correct storage unit ID. You can check what storages you can
    add wines to from the '/storages/get' endpoint.
    """
    # Check if storage unit is valid
    if not await verify_storage_exists(db_conn=db_conn, storage_id=wine_data.storage_unit):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Storage unit is not found.")

    # Inspect if the wine is already in the wines table
    if not await verify_wine_in_db(db_conn=db_conn, name=wine_data.wine_info.name, vintage=wine_data.wine_info.vintage):
        # If not, add data to the wines table
        await add_wine_to_db(db_conn=db_conn, wine_info=wine_data.wine_info)

    # Retrieve wine ID from the wines table
    wine_id = await get_bottle_id(db_conn=db_conn, name=wine_data.wine_info.name, vintage=wine_data.wine_info.vintage)

    # Insert all info into the cellar table
    await add_bottle_to_cellar(db_conn=db_conn, wine_id=wine_id, owner_id=current_user.id, wine_data=wine_data)

    return "Bottle has successfully been added to the DB"


@router.post("/wine_in_cellar/add_rating", dependencies=[Security(get_current_active_user)])
async def add_a_rating(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                       current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                       wine_id: int,
                       rating: RatingModel) -> str:
    """
    Adds a rating to your DB. Note that if you've drunk a bottle, you can make use of the '/wine_in_cellar/consumed'
    endpoint to both add a rating and update your storage.
    """
    # Verify the wine exists in the DB
    if not await wine_in_db(db_conn=db_conn, wine_id=wine_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Wine with wine_id: {wine_id} is not found in the DB. Make sure to use an "
                                   f"existing wine ID in order to rate the correct wine")
    await add_rating_to_db(db_conn=db_conn, user_id=current_user.id, wine_id=wine_id, rating=rating)
    return "Rating has successfully been added to the DB"


@router.get("/wine_in_cellar/get_wine_ratings", dependencies=[Security(get_current_active_user)])
async def get_wine_rating(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                          current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                          wine_id: int | None = None,
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


@router.get("/wine_in_cellar/get_your_ratings", dependencies=[Security(get_current_active_user)])
async def get_your_ratings(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                           current_user: Annotated[OwnerModel, Depends(get_current_active_user)]
                           ) -> list[RatingInDbModel]:
    """
    Retrieves all your ratings for all wines/bottles.
    """
    # Retrieve the ratings from the DB
    return db_conn.execute_query_select(query="SELECT * FROM cellar.ratings WHERE rater_id = %(rater_id)s",
                                        params={"rater_id": current_user.id}, get_fields=True)


@router.delete("/wine_in_cellar/remove_rating", dependencies=[Security(get_current_active_user)])
async def delete_a_rating(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                          current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                          rating_id: int) -> str:
    """
    Removes one of your ratings from the DB. Make sure to provide a valid rating_id. Make use of the
    '/wine_in_cellar/get_wine_ratings' endpoint with the 'only_your_ratings' argument set to True in order to see your
    ratings on a specific wine. Or exploit the '/wine_in_cellar/get_your_ratings' endpoint for a full overview of your
    ratings.
    """
    # Verify the wine exists in the DB
    if not await rating_in_db(db_conn=db_conn, rating_id=rating_id, user_id=current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Rating with rating_id: {rating_id} is not found in the DB or the rating is not "
                                   f"not provided by you. Make sure to use an valid rating ID in order to delete "
                                   f"the correct rating")
    db_conn.execute_query(query="DELETE FROM cellar.ratings WHERE id = %(rating_id)s",
                          params={"rating_id": rating_id})
    return "Rating has successfully been removed from the DB"


@router.patch("/wine_in_cellar/consumed", dependencies=[Security(get_current_active_user)])
async def remove_consumed_from_stock(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                                     current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                                     bottle_data: ConsumedBottleModel,
                                     rate_bottle: bool = True,
                                     rating: RatingModel | None = None) -> str:
    """
    Removes a bottle from your cellar, if the 'rate_bottle' flag is set to True, the rating argument is required, else it
    will be ignored and can be left in the default state.
    """
    # Verify the wine exists in the DB
    if not await wine_in_db(db_conn=db_conn, wine_id=bottle_data.wine_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Wine with wine_id: {bottle_data.wine_id} is not found in the DB. Make sure to use "
                                   f"an existing wine ID in order to mark the correct wine as consumed")
    # Add a rating to the DB if the data is provided
    if rate_bottle:
        await add_rating_to_db(db_conn=db_conn, user_id=current_user.id, wine_id=bottle_data.wine_id, rating=rating)

    await update_quantity_in_cellar(db_conn=db_conn, wine_id=bottle_data.wine_id, bottle_data=bottle_data, add=False)
    return "Consumed bottle is updated in the DB"

