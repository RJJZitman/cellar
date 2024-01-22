from fastapi import HTTPException, status
from mysql.connector.errors import DataError


from ..db_utils import MariaDB
from ..models import OwnerModel, WinesModel, CellarInModel, GeographicInfoModel, RatingModel, ConsumedBottleModel


def unpack_geo_info(geographic_info: GeographicInfoModel) -> str:
    return ",\t".join(f"{k}: {v}" for k, v in geographic_info.dict().items())


async def get_storage_id(db_conn: MariaDB, current_user: OwnerModel, location: str, description: str) -> int:
    storage_id = db_conn.execute_query_select(query="SELECT id FROM cellar.storages "
                                                    "WHERE location = %(location)s "
                                                    "  AND description = %(description)s "
                                                    "  AND owner_id = %(owner_id)s",
                                              params={"location": location, "description": description,
                                                      "owner_id": current_user.id})
    try:
        return storage_id[0]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Storage unit is not found.")


async def verify_storage_exists_for_user(db_conn: MariaDB, storage_id: int, user_id: int) -> bool:
    info = db_conn.execute_query_select(query="SELECT location, description "
                                              "FROM cellar.storages "
                                              "WHERE id = %(storage_id)s AND owner_id = %(user_id)s",
                                        params={"storage_id": storage_id, "user_id": user_id},
                                        get_fields=True)
    if len(info):
        return True
    else:
        return False


async def verify_empty_storage_unit(db_conn: MariaDB, storage_id: int) -> bool:
    storage = db_conn.execute_query_select(query="SELECT * FROM cellar.cellar "
                                                 "WHERE storage_unit = %(storage_id)s",
                                           params={"storage_id": storage_id},
                                           get_fields=True)
    if len(storage):
        # Raise 400 error for non-empty storage unit.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Storage unit is not empty. Make sure to either drink it all or move the bottles "
                                   f"to another storage unit. Bottles left in unit: {storage}")
    else:
        return True


async def verify_wine_in_db(db_conn: MariaDB, name: str, vintage: int) -> bool:
    wine = db_conn.execute_query_select(query="SELECT * FROM cellar.wines "
                                              "WHERE name = %(name)s "
                                              "AND vintage = %(vintage)s",
                                        params={"name": name, "vintage": vintage})
    if wine:
        return True
    else:
        return False


async def add_wine_to_db(db_conn: MariaDB, wine_info: WinesModel):
    db_conn.execute_query(query="INSERT INTO cellar.wines (name, vintage, grapes, type, drink_from, drink_before, "
                                "                          alcohol_vol_perc, geographic_info, quality_signature) "
                                "VALUES "
                                "(%(name)s, %(vintage)s, %(grapes)s, %(type)s, %(drink_from)s, %(drink_before)s, "
                                "%(alcohol_vol_perc)s, %(geographic_info)s, %(quality_signature)s)",
                          params={"name": wine_info.name, "vintage": wine_info.vintage, "grapes": wine_info.grapes,
                                  "type": wine_info.type, "drink_from": wine_info.drink_from,
                                  "drink_before": wine_info.drink_before,
                                  "alcohol_vol_perc": wine_info.alcohol_vol_perc,
                                  "geographic_info": unpack_geo_info(wine_info.geographic_info),
                                  "quality_signature": wine_info.quality_signature})
    return "Wine has successfully been added to the DB wines table"


async def get_bottle_id(db_conn: MariaDB, name: str, vintage: int) -> bool:
    wine = db_conn.execute_query_select(query="SELECT id FROM cellar.wines "
                                              "WHERE name = %(name)s "
                                              "AND vintage = %(vintage)s",
                                        params={"name": name, "vintage": vintage})
    try:
        return wine[0][0]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"The requested bottle is not found.")


async def verify_bottle_exists_in_storage_unit(db_conn: MariaDB, wine_id: int, storage_unit: int, bottle_size: float
                                               ) -> bool:
    in_storage_unit = db_conn.execute_query_select(query="SELECT * FROM cellar.cellar "
                                                         "WHERE wine_id = %(wine_id)s "
                                                         "   AND storage_unit = %(storage_unit)s "
                                                         "   AND bottle_size_cl = %(bottle_size_cl)s",
                                                   params={"wine_id": wine_id, "storage_unit": storage_unit,
                                                           "bottle_size_cl": bottle_size})
    if len(in_storage_unit):
        return True
    else:
        return False


async def update_quantity_in_cellar(db_conn: MariaDB, wine_id: int, bottle_data: CellarInModel | ConsumedBottleModel,
                                    add: bool) -> None:
    quantity_operator = "+" if add else "-"
    params = {"quantity": str(bottle_data.quantity),
              "wine_id": str(wine_id),
              "storage_unit": str(bottle_data.storage_unit),
              "bottle_size_cl": str(bottle_data.bottle_size_cl)}
    query_conditions = ("wine_id = %(wine_id)s "
                        "AND storage_unit = %(storage_unit)s "
                        "AND bottle_size_cl = %(bottle_size_cl)s")
    try:
        # Update the quantity by adding or subtracting the desired value
        db_conn.execute_query(query=f"UPDATE cellar.cellar "
                                    f"SET quantity = quantity {quantity_operator} %(quantity)s "
                                    f"WHERE {query_conditions}",
                              params=params)
        # Remove record matching the bottle if quantity is brought back to zero
        db_conn.execute_query(query=f"DELETE FROM cellar.cellar "
                                    f"WHERE quantity = 0 AND {query_conditions}",
                              params=params)

    except DataError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="There aren't that many bottles left in your cellar or storage unit. Make sure to "
                                   "update your stock per storage unit.")


async def add_bottle_to_cellar(db_conn: MariaDB, wine_id: int, owner_id: int, wine_data: CellarInModel):
    # Verify if the bottle already exists in the storage unit
    if await verify_bottle_exists_in_storage_unit(db_conn=db_conn, wine_id=wine_id,
                                                  storage_unit=wine_data.storage_unit,
                                                  bottle_size=wine_data.bottle_size_cl):
        # Update the quantity by adding the new value
        await update_quantity_in_cellar(db_conn=db_conn, wine_id=wine_id, bottle_data=wine_data, add=True)
    else:
        # Insert the data as a new entry to the DB
        db_conn.execute_query(query="INSERT INTO cellar.cellar (wine_id, storage_unit, owner_id, bottle_size_cl, "
                                    "                           quantity, drink_from, drink_before) "
                                    "VALUES (%(wine_id)s, %(storage_unit)s, %(owner_id)s, %(bottle_size_cl)s, "
                                    "        %(quantity)s, %(drink_from)s, %(drink_before)s)",
                              params={"wine_id": wine_id, "storage_unit": wine_data.storage_unit, "owner_id": owner_id,
                                      "bottle_size_cl": wine_data.bottle_size_cl, "quantity": wine_data.quantity,
                                      "drink_from": wine_data.wine_info.drink_from,
                                      "drink_before": wine_data.wine_info.drink_before})


async def wine_in_db(db_conn: MariaDB, wine_id: int) -> bool:
    wine = db_conn.execute_query_select(query="SELECT * FROM cellar.wines WHERE id = %(wine_id)s",
                                        params={"wine_id": wine_id})
    if len(wine):
        return True
    else:
        return False


async def rating_in_db(db_conn: MariaDB, rating_id: int, user_id: int) -> bool:
    rating = db_conn.execute_query_select(query="SELECT * FROM cellar.ratings "
                                                "WHERE id = %(rating_id)s AND rater_id = %(rater_id)s",
                                          params={"rating_id": rating_id, "rater_id": user_id})
    if len(rating):
        return True
    else:
        return False


async def add_rating_to_db(db_conn: MariaDB, user_id: int, wine_id: int, rating: RatingModel):
    db_conn.execute_query(query="INSERT INTO cellar.ratings (rater_id, wine_id, rating, drinking_date, comments) "
                                "VALUES (%(rater_id)s, %(wine_id)s, %(rating)s, %(drinking_date)s, %(comments)s)",
                          params={"rater_id": user_id, "wine_id": wine_id, "rating": rating.rating,
                                  "drinking_date": rating.drinking_date, "comments": rating.comments})


