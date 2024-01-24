from typing import Annotated

from fastapi import HTTPException, status
from fastapi import APIRouter, Depends, Security, Query

from .cellar_funcs import (get_storage_id, verify_storage_exists_for_user, verify_empty_storage_unit, verify_wine_in_db,
                           add_wine_to_db, get_bottle_id, add_bottle_to_cellar, wine_in_db, add_rating_to_db,
                           update_quantity_in_cellar)

from ..db_utils import MariaDB
from ..constants import DB_CONN
from ..authentication import get_current_active_user
from ..models import OwnerModel, StorageInModel, CellarInModel, RatingModel, ConsumedBottleModel


router = APIRouter(prefix="/cellar",
                   tags=["cellar"],
                   dependencies=[Security(get_current_active_user, scopes=['CELLAR:READ', 'CELLAR:WRITE'])],
                   responses={404: {"description": "Not Found"}})


@router.post("/storages/add", dependencies=[Security(get_current_active_user)])
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


@router.delete("/storages/delete", dependencies=[Security(get_current_active_user)])
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
    if await verify_empty_storage_unit(db_conn=db_conn, storage_id=storage_id[0]):
        db_conn.execute_query(query="DELETE FROM cellar.storages "
                                    "WHERE location = %(location)s "
                                    "  AND description = %(description)s "
                                    "  AND owner_id = %(owner_id)s",
                              params={"location": location, "description": description, "owner_id": current_user.id})

    return "Storage unit has successfully been removed from the DB"


@router.post("/wine_in_cellar/add", dependencies=[Security(get_current_active_user)])
async def add_wine_to_cellar(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                             current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                             wine_data: CellarInModel) -> str:
    """
    Adds bottles to your cellar. Make sure to provide the correct storage unit ID. You can check what storages you can
    add wines to from the '/storages/get' endpoint.
    """
    # Check if storage unit is valid
    if not await verify_storage_exists_for_user(db_conn=db_conn, storage_id=wine_data.storage_unit,
                                                user_id=current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Storage unit is not found for your particular user.")

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


@router.patch("/wine_in_cellar/move", dependencies=[Security(get_current_active_user)])
async def move_bottle_to_other_storage(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                                       current_user: Annotated[OwnerModel, Depends(get_current_active_user)],
                                       cellar_id: int,
                                       new_storage_unit: int) -> str:
    """
    Move a bottle from one storage unit to another.
    """
    if verify_storage_exists_for_user(db_conn=db_conn, storage_id=new_storage_unit, user_id=current_user.id):
        db_conn.execute_query(query=("UPDATE cellar.cellar "
                                     "SET storage_unit = %(storage_unit)s WHERE id = %(cellar_id)s"),
                              params={"storage_unit": new_storage_unit, "cellar_id": cellar_id})
        return f"Bottle has successfully been transferred to storage unit {new_storage_unit}"
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Storage unit is not found for your particular user.")
