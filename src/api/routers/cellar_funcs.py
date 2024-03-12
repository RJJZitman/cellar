from typing import Any

from fastapi import HTTPException, status
from mysql.connector.errors import DataError

from db.jdbc_interface import JdbcDbConn

from ..models import WinesModel, CellarInModel, GeographicInfoModel, RatingModel, ConsumedBottleModel, CellarOutModel


def unpack_geo_info(geographic_info: GeographicInfoModel) -> str:
    """Unpacks the data in a GeographicInfoModel instance and returns it as a string"""
    return ",\t".join(f"{k}: {v}" for k, v in geographic_info.dict().items())


async def get_storage_id(db_conn: JdbcDbConn, current_user_id: int, location: str, description: str) -> int:
    """
    Retrieves the storage ID for a specific storage for a specific user.

    :param db_conn: MariaDB instance to connect to the DB
    :param current_user_id: db id of the current user
    :param location: storage unit location
    :param description: storage unit description
    :return: the storage id
    """
    storage_id = db_conn.execute_query_select(query="SELECT id FROM cellar.storages "
                                                    "WHERE location = %(location)s "
                                                    "  AND description = %(description)s "
                                                    "  AND owner_id = %(owner_id)s",
                                              params={"location": location, "description": description,
                                                      "owner_id": current_user_id})
    try:
        return storage_id[0]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit is not found.")


async def verify_storage_exists_for_user(db_conn: JdbcDbConn, storage_id: int, user_id: int) -> bool:
    """
    Verifies whether a provided storage id exists for a specific user

    :param db_conn: MariaDB instance to connect to the DB
    :param storage_id: id of storage unit
    :param user_id: id of user
    :return: True if the storage unit exists for the user, False if not
    """
    info = db_conn.execute_query_select(query="SELECT location, description "
                                              "FROM cellar.storages "
                                              "WHERE id = %(storage_id)s AND owner_id = %(user_id)s",
                                        params={"storage_id": storage_id, "user_id": user_id})
    if len(info):
        return True
    else:
        return False


async def verify_empty_storage_unit(db_conn: JdbcDbConn, storage_id: int) -> bool:
    """
    Verifies whether a storage unit is empty

    :param db_conn: MariaDB instance to connect to the DB
    :param storage_id: id of storage unit
    :return: True if the storage unit is empty,raises an HTTP_400 error if not
    """
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


async def verify_wine_in_db(db_conn: JdbcDbConn, name: str, vintage: int) -> bool:
    """
    Verifies whether a wine already exists in the DB in the wines table

    :param db_conn: MariaDB instance to connect to the DB
    :param name: name of the wine (beer)
    :param vintage: year of production/harvest
    :return: True if the wine exists in the wines table, False if not
    """
    wine = db_conn.execute_query_select(query="SELECT * FROM cellar.wines "
                                              "WHERE name = %(name)s "
                                              "AND vintage = %(vintage)s",
                                        params={"name": name, "vintage": vintage})
    if wine:
        return True
    else:
        return False


async def add_wine_to_db(db_conn: JdbcDbConn, wine_info: WinesModel) -> str:
    """
    Adds a wine to the DB wine table

    :param db_conn: MariaDB instance to connect to the DB
    :param wine_info: name of the wine (beer)
    :return: True if the wine exists in the wines table, False if not
    """
    db_conn.execute_query("INSERT INTO cellar.wines (name, vintage, grapes, type, drink_from, drink_before, "
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


async def get_bottle_id(db_conn: JdbcDbConn, name: str, vintage: int) -> int:
    """
    Retrieves the ID of a wine from the database

    :param db_conn: MariaDB instance to connect to the DB
    :param name: name of the wine
    :param vintage: vintage of the wine
    :return: the id of the wine, raises a 404 error if the requested wine is not found in the db
    """
    wine = db_conn.execute_query_select(query="SELECT id FROM cellar.wines "
                                              "WHERE name = %(name)s "
                                              "AND vintage = %(vintage)s",
                                        params={"name": name, "vintage": vintage})
    try:
        return wine[0][0]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"The requested wine is not found.")


async def verify_bottle_exists_in_storage_unit(db_conn: JdbcDbConn, wine_id: int, storage_unit: int, bottle_size: float
                                               ) -> bool:
    """
    Checks whether a bottle with identical size and wine_id is already stored in a storage unit

    :param db_conn: MariaDB instance to connect to the DB
    :param wine_id: id of the wine from the wines table
    :param storage_unit: storage unit id
    :param bottle_size: bottle size in cl
    :return: True if the bottle is already stored in the cellar, False if not
    """
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


async def update_quantity_in_cellar(db_conn: JdbcDbConn, wine_id: int, bottle_data: CellarInModel | ConsumedBottleModel,
                                    add: bool) -> None:
    """
    Updates the quantity of stored bottles in the cellar table. If the quantity is updated to 0, the entry is removed.

    :param db_conn: MariaDB instance to connect to the DB
    :param wine_id: id of the wine from the wines table
    :param bottle_data: specific info on the bottle. The required info is stored similarly in both type-hinted models
    :param add: add the provided quantity to the db if True, subtracts if False
    """
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
        db_conn.execute_query(f"UPDATE cellar.cellar SET quantity = quantity {quantity_operator} %(quantity)s "
                              f"WHERE {query_conditions}",
                              params=params)
        # Remove record matching the bottle if quantity is brought back to zero
        db_conn.execute_query(f"DELETE FROM cellar.cellar WHERE quantity = 0 AND {query_conditions}",
                              params=params)

    except DataError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="There aren't that many bottles left in your cellar or storage unit. Make sure to "
                                   "update your stock per storage unit.")


async def add_bottle_to_cellar(db_conn: JdbcDbConn, wine_id: int, owner_id: int, wine_data: CellarInModel) -> None:
    """
    Adds new bottles to the DB by either adding a new entry or updating the quantity of an existing one

    :param db_conn: MariaDB instance to connect to the DB
    :param wine_id: id of the wine from the wines table
    :param owner_id: id of user/bottle owner
    :param wine_data: wine specific data
    """
    # Verify if the bottle already exists in the storage unit
    if await verify_bottle_exists_in_storage_unit(db_conn=db_conn, wine_id=wine_id,
                                                  storage_unit=wine_data.storage_unit,
                                                  bottle_size=wine_data.bottle_size_cl):
        # Update the quantity by adding the new value
        await update_quantity_in_cellar(db_conn=db_conn, wine_id=wine_id, bottle_data=wine_data, add=True)
    else:
        # Insert the data as a new entry to the DB
        db_conn.execute_query("INSERT INTO cellar.cellar (wine_id, storage_unit, owner_id, bottle_size_cl, "
                              "                           quantity, drink_from, drink_before) "
                              "VALUES (%(wine_id)s, %(storage_unit)s, %(owner_id)s, %(bottle_size_cl)s, "
                              "        %(quantity)s, %(drink_from)s, %(drink_before)s)",
                              params={"wine_id": wine_id, "storage_unit": wine_data.storage_unit, "owner_id": owner_id,
                                      "bottle_size_cl": wine_data.bottle_size_cl, "quantity": wine_data.quantity,
                                      "drink_from": wine_data.wine_info.drink_from,
                                      "drink_before": wine_data.wine_info.drink_before})


async def wine_in_db(db_conn: JdbcDbConn, wine_id: int) -> bool:
    """
    Verifies whether a wine exists in the DB based on the id

    :param db_conn: MariaDB instance to connect to the DB
    :param wine_id: id of the wine from the wines table
    :return: True if the provided wine id is known, False if not
    """
    wine = db_conn.execute_query_select(query="SELECT * FROM cellar.wines WHERE id = %(wine_id)s",
                                        params={"wine_id": wine_id})
    if len(wine):
        return True
    else:
        return False


async def rating_in_db(db_conn: JdbcDbConn, rating_id: int, user_id: int) -> bool:
    """
    Verifies whether a wine exists in the DB based on the id of both the rating and the rater i.e., bottle owner

    :param db_conn: MariaDB instance to connect to the DB
    :param rating_id: id of the rating from the ratings table
    :param user_id: id of user/bottle owner
    :return: True if the provided wine id is known, False if not
    """
    rating = db_conn.execute_query_select(query="SELECT * FROM cellar.ratings "
                                                "WHERE id = %(rating_id)s AND rater_id = %(rater_id)s",
                                          params={"rating_id": rating_id, "rater_id": user_id})
    if len(rating):
        return True
    else:
        return False


async def add_rating_to_db(db_conn: JdbcDbConn, user_id: int, wine_id: int, rating: RatingModel) -> None:
    """
    Adds a rating to the db

    :param db_conn: MariaDB instance to connect to the DB
    :param user_id: id of user/bottle owner
    :param wine_id: id of the wine from the wines table
    :param rating: rating data
    :return: True if the provided wine id is known, False if not
    """
    db_conn.execute_query("INSERT INTO cellar.ratings (rater_id, wine_id, rating, drinking_date, comments) "
                          "VALUES (%(rater_id)s, %(wine_id)s, %(rating)s, %(drinking_date)s, %(comments)s)",
                          params={"rater_id": user_id, "wine_id": wine_id, "rating": rating.rating,
                                  "drinking_date": rating.drinking_date, "comments": rating.comments})


def get_cellar_out_data(db_conn: JdbcDbConn, params: dict[str, Any] | None = None, where: str | None = None
                        ) -> list[CellarOutModel.schema_json()]:
    """
    Retrieves data from the cellar table. Additional where conditions and query parameters can be added to complete the
    query

    :param db_conn: MariaDB instance to connect to the DB
    :param params: additional params to complete the query
    :param where: optional space for where statements to complement the query
    :return: a list of entries from the cellar DB, formatted tot the CellarOutModel schema
    """
    query = ("SELECT w.name AS name, w.vintage AS vintage, "
             "       c.id AS cellar_id, "
             "       c.storage_unit AS storage_unit, c.quantity AS quantity,"
             "       c.bottle_size_cl AS bottle_size_cl,"
             "       c.wine_id AS wine_id, c.owner_id AS owner_id,"
             "       c.drink_from AS drink_from, c.drink_before AS drink_before "
             "FROM cellar.cellar AS c "
             "LEFT JOIN cellar.wines AS w "
             "    ON w.id = c.wine_id ")
    if where:
        query += where
    else:
        params = None
    return db_conn.execute_query_select(query=query, params=params, get_fields=True)
