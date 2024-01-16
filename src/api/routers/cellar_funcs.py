import json

from fastapi import HTTPException, status

from ..db_utils import MariaDB
from ..models import OwnerModel, WinesModel, CellarInModel, GeographicInfoModel


def unpack_geo_info(geographic_info: GeographicInfoModel) -> str:
    return ",\t".join(f"{k}: {v}" for k, v in geographic_info.dict().items())


async def get_storage_id(db_conn: MariaDB, current_user: OwnerModel, location: str, description: str) -> int:
    storage_id = db_conn.execute_query_select(query=f"SELECT id FROM cellar.storages "
                                                    f"WHERE location = :location "
                                                    f"AND description = :description "
                                                    f"AND owner_id = :owner_id",
                                              params={"location": location, "description": description,
                                                      "owner_id": current_user.id})
    try:
        return storage_id[0]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Storage unit is not found.")


async def verify_storage_exists(db_conn: MariaDB, storage_id: int) -> bool:
    info = db_conn.execute_query_select(query=f"SELECT location, description "
                                              f"FROM cellar.storages "
                                              f"WHERE id = :storage_id",
                                        params={"storage_id": storage_id},
                                        get_fields=True)
    if len(info):
        return True
    else:
        return False


async def verify_empty_storage_unit(db_conn: MariaDB, storage_id: int) -> bool:
    storage = db_conn.execute_query_select(query="SELECT * FROM cellar.cellar "
                                                 "WHERE storage_unit = :storage_id",
                                           params={"storage_id": str(storage_id)})
    if storage:
        # Raise 400 error for non-empty storage unit.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Storage unit is not empty. Make sure to either drink it all or move the bottles "
                                   f"to another storage unit. Bottles left in unit: {[bottle for bottle in storage]}")
    else:
        return True


async def verify_wine_in_db(db_conn: MariaDB, name: str, vintage: int) -> bool:
    wine = db_conn.execute_query_select(query=f"SELECT * FROM cellar.wines "
                                              f"WHERE name = :name "
                                              f"AND vintage = :vintage",
                                        params={"name": name, "vintage": vintage})
    if wine:
        return True
    else:
        return False


async def add_wine_to_db(db_conn: MariaDB, wine_info: WinesModel):
    db_conn.execute_query(query=f"INSERT INTO cellar.wines (name, vintage, grapes, type, drink_from, drink_before, "
                                f"                          alcohol_vol_perc, geographic_info, quality_signature) "
                                f"VALUES "
                                f"(:name, :vintage, :grapes, :type, :drink_from, :drink_before, :alcohol_vol_perc, "
                                f" :geographic_info, :quality_signature)",
                          params={"name": wine_info.name, "vintage": wine_info.vintage, "grapes": wine_info.grapes,
                                  "type": wine_info.type, "drink_from": wine_info.drink_from,
                                  "drink_before": wine_info.drink_before,
                                  "alcohol_vol_perc": wine_info.alcohol_vol_perc,
                                  "geographic_info": unpack_geo_info(wine_info.geographic_info),
                                  "quality_signature": wine_info.quality_signature})


async def get_bottle_id(db_conn: MariaDB, name: str, vintage: int) -> bool:
    wine = db_conn.execute_query_select(query=f"SELECT id FROM cellar.wines "
                                              f"WHERE name = :name "
                                              f"AND vintage = :vintage",
                                        params={"name": name, "vintage": vintage})
    try:
        return wine[0][0]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"The requested bottle is not found.")


async def verify_bottle_exists_in_storage_unit(db_conn: MariaDB, wine_id: int, storage_unit: int, bottle_size: float
                                               ) -> bool:
    in_storage_unit = db_conn.execute_query_select(query="SELECT * FROM cellar.cellar "
                                                         "WHERE id = :wine_id "
                                                         "   AND storage_unit = :storage_unit "
                                                         "   AND bottle_size_cl = :bottle_size_cl",
                                                   params={"wine_id": wine_id, "storage_unit": storage_unit,
                                                           "bottle_size_cl": bottle_size})
    if len(in_storage_unit):
        return True
    else:
        return False


async def add_bottle_to_cellar(db_conn: MariaDB, wine_id: int, owner_id: int, wine_data: CellarInModel):
    # Verify if the bottle already exists in the storage unit
    if await verify_bottle_exists_in_storage_unit(db_conn=db_conn, wine_id=wine_id,
                                                  storage_unit=wine_data.storage_unit,
                                                  bottle_size=wine_data.bottle_size_cl):
        # Update the quantity by adding the new value
        db_conn.execute_query(query=f"UPDATE cellar.cellar "
                                    f"SET quantity = quantity + :quantity "
                                    f"WHERE wine_id = :wine_id "
                                    f"  AND storage_unit = :wine_data.storage_unit "
                                    f"  AND bottle_size_cl = :wine_data.bottle_size_cl",
                              params={"quantity": str(wine_data.quantity), "wine_id": str(wine_id),
                                      "storage_unit": str(wine_data.storage_unit),
                                      "bottle_size_cl": str(wine_data.bottle_size_cl)})
    else:
        # Insert the data as a new entry to the DB
        db_conn.execute_query(query="INSERT INTO cellar.cellar (wine_id, storage_unit, owner_id, bottle_size_cl, "
                                    "                           quantity, drink_from, drink_before) "
                                    "VALUES (:wine_id, :storage_unit, :owner_id, :bottle_size_cl, :quantity, "
                                    "        :drink_from, :drink_before)",
                              params={"wine_id": wine_id, "storage_unit": wine_data.storage_unit, "owner_id": owner_id,
                                      "bottle_size_cl": wine_data.bottle_size_cl, "quantity": wine_data.quantity,
                                      "drink_from": wine_data.wine_info.drink_from,
                                      "drink_before": wine_data.wine_info.drink_before})
