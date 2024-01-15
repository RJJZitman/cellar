from fastapi import HTTPException, status

from ..db_utils import MariaDB
from ..models import OwnerModel


async def get_storage_id(db_conn: MariaDB, current_user: OwnerModel, location: str, description: str) -> int:
    storage_id = db_conn.execute_query_select(query=f"SELECT id FROM cellar.storages "
                                                    f"WHERE location = '{location}' "
                                                    f"AND description = '{description}' "
                                                    f"AND owner_id = '{current_user.id}'")
    try:
        return storage_id[0]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Storage unit is not found.")


async def verify_storage_exists(db_conn: MariaDB, storage_id: int) -> bool:
    info = db_conn.execute_query_select(query=f"SELECT location, description "
                                              f"FROM cellar.storages "
                                              f"WHERE id = '{storage_id}'",
                                        get_fields=True)
    if len(info):
        return True
    else:
        return False


async def verify_empty_storage_unit(db_conn: MariaDB, storage_id: int) -> bool:
    storage = db_conn.execute_query_select(query=f"SELECT * FROM cellar.cellar "
                                                 f"WHERE storage_unit = '{storage_id}'")
    if storage:
        # Raise 400 error for non-empty storage unit.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Storage unit is not empty. Make sure to either drink it all or move the bottles "
                                   f"to another storage unit. Bottles left in unit: {[bottle for bottle in storage]}")
    else:
        return True


async def verify_wine_in_db(db_conn: MariaDB, name: str, vintage: int) -> bool:
    wine = db_conn.execute_query_select(query=f"SELECT * FROM cellar.wines "
                                              f"WHERE name = '{name}' "
                                              f"AND vintage = '{vintage}'")
    if wine:
        return True
    else:
        return False
