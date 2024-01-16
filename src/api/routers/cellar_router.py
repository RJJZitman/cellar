from typing import Annotated

from fastapi import HTTPException, status
from fastapi import APIRouter, Depends, Security, Query

from .cellar_funcs import (get_storage_id, verify_storage_exists, verify_empty_storage_unit, verify_wine_in_db,
                           add_wine_to_db, get_bottle_id, add_bottle_to_cellar)

from ..db_utils import MariaDB
from ..constants import DB_CONN
from ..authentication import get_current_active_user
from ..models import OwnerModel, StorageInModel, StorageOutModel, CellarInModel


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
    return db_conn.execute_query_select(query='SELECT * FROM cellar.owners', get_fields=True)


@router.get("/storages/get", response_model=list[StorageOutModel], dependencies=[Security(get_current_active_user)])
async def get_storage_units(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                            current_user: Annotated[OwnerModel, Depends(get_current_active_user)]):
    """
    Retrieve all owners registered within the DB.
    Required scope(s): CELLAR:READ
    """
    return db_conn.execute_query_select(query="SELECT * FROM cellar.storages WHERE owner_id = :owner_id",
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
                                "VALUES (:owner_id, :location, :description)",
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
        db_conn.execute_query(query=f"DELETE FROM cellar.storages "
                                    f"WHERE location = :location "
                                    f"  AND description = :description "
                                    f"  AND owner_id = :owner_id",
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
                            detail=f"Storage unit is not found.")

    # Inspect if the wine is already in the wines table
    if not await verify_wine_in_db(db_conn=db_conn, name=wine_data.wine_info.name, vintage=wine_data.wine_info.vintage):
        # If not, add data to the wines table
        await add_wine_to_db(db_conn=db_conn, wine_info=wine_data.wine_info)

    # Retrieve wine ID from the wines table
    wine_id = await get_bottle_id(db_conn=db_conn, name=wine_data.wine_info.name, vintage=wine_data.wine_info.vintage)

    # Insert all info into the cellar table
    await add_bottle_to_cellar(db_conn=db_conn, wine_id=wine_id, owner_id=current_user.id, wine_data=wine_data)

    return "Bottle has successfully been added to the DB"
