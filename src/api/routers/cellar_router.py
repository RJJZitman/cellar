from typing import Annotated

from fastapi import APIRouter, Depends, Security, Query

from ..db_utils import MariaDB
from ..constants import DB_CONN
from ..authentication import get_current_active_user
from ..models import OwnerModel, StorageInModel, StorageOutModel


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
    return db_conn.execute_query_select(query='select * from cellar.owners', get_fields=True)


@router.get("/storages/get", response_model=list[StorageOutModel], dependencies=[Security(get_current_active_user)])
async def get_storage_units(db_conn: Annotated[MariaDB, Depends(DB_CONN)]):
    """
    Retrieve all owners registered within the DB.
    Required scope(s): CELLAR:READ
    """
    return db_conn.execute_query_select(query='select * from cellar.storages', get_fields=True)


@router.post("/storages/add", dependencies=[Security(get_current_active_user, scopes=['CELLAR:WRITE'])])
async def post_storage_unit(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                            storage_data: StorageInModel) -> str:
    """
    Add a storage unit to the DB.
    Required scope(s): CELLAR:READ, CELLAR:WRITE
    """
    db_conn.execute_query(query=f"INSERT INTO cellar.storages (location, description) VALUES "
                                f"('{storage_data.location}', '{storage_data.description}')")

    return "Storage unit has successfully been added to the DB"


@router.delete("/storages/delete", dependencies=[Security(get_current_active_user, scopes=['CELLAR:WRITE'])])
async def delete_storage_unit(db_conn: Annotated[MariaDB, Depends(DB_CONN)],
                              location: Annotated[str, Query(max_length=200)],
                              description: Annotated[str, Query(max_length=200)]) -> str:
    """
    Delete a storage unit to the DB. Provide the location and description of the storage unit to select which unit should be deleted.
    Required scope(s): CELLAR:READ, CELLAR:WRITE
    """
    db_conn.execute_query(query=f"DELETE FROM cellar.storages "
                                f"WHERE location = '{location}' "
                                f"AND description = '{description}'")

    return "Storage unit has successfully been removed from the DB"
