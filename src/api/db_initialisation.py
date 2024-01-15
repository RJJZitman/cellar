import os
import time
import yaml

from .db_utils import MariaDB
from .constants import SRC, SQL
from .models import DbConnModel
from .authentication import get_password_hash


def database_service(restarted: bool = True) -> bool:
    """
    If requested, restarts the DB service and waits a fixed amount of time to allow for the DB to fully set-up.

    :param restarted: Denotes whether the DB service should be restarted
    :return: whether the db service was restarted
    """
    if restarted:
        os.system('brew services restart mariadb')
        time.sleep(15)
        return True
    else:
        return False


def setup_new_database(db_conn: MariaDB) -> None:
    """
    Drops the cellar DB and re-builds a clean/empty version.

    :param db_conn: The MariaDB JDBC connection
    """
    db_conn.execute_query("drop database if exists cellar;")
    db_conn.execute_sql_file(file_path=f'{SQL}create_databases.sql')
    db_conn.execute_sql_file(file_path=f'{SQL}create_tables.sql',
                             multi=True)


def make_db_admin_user(db_conn: MariaDB) -> None:
    """
    Creates an admin user from the env file for credentials for ultimate DB/API access.

    :param db_conn: The MariaDB JDBC connection
    """
    with open(f'{SRC}env.yml', 'r') as file:
        env = yaml.safe_load(file)
    print(db_conn.execute_query_select("select * from cellar.owners"))
    db_conn.execute_query(query=f"INSERT INTO cellar.owners (name, username, password, scopes, is_admin, enabled) "
                                f"VALUES "
                                f"('{env['DB_USER_NAME']}', '{env['DB_USER']}', "
                                f"'{get_password_hash(password=env['DB_PW'])}', '', 1, 1)")
    print(db_conn.execute_query_select(f"select * from cellar.owners where username='{env['DB_USER_NAME']}'"))


def check_for_cellar_db(db_conn: MariaDB) -> bool:
    """
    Verifies whether the cellar DB exists and contains expected tables.

    :param db_conn: The MariaDB JDBC connection
    """
    existing_dbs = db_conn.execute_query_select(query="show databases")
    if sum([1 for existing_db in existing_dbs if existing_db[0] == "cellar"]):
        print("cellar DB has been found")
        db_conn.execute_query(query="use cellar")
        existing_tables = db_conn.execute_query_select(query="show tables")
        if sum([1 for _ in existing_tables]) < 5:
            print("cellar schema is incomplete and therefore dropped")
            db_conn.execute_query(query="drop schema cellar")
            return False
        return True
    else:
        return False


def check_for_admin_user(db_conn: MariaDB) -> bool:
    """
    Verifies whether the admin user exists.

    :param db_conn: The MariaDB JDBC connection
    """
    owners = db_conn.execute_query_select(query="SELECT * FROM cellar.owners")
    if owners:
        return True
    else:
        print("No wine owners are found, DB is being re-instantiated")
        return False


def db_setup(db_creds: DbConnModel, restarted: bool = True) -> None:
    """
    Works towards a state wherein the cellar DB exists, contains the expected tables and ensures the admin user exists.

    :param db_creds: Credentials for the MariaDB JDBC connection
    :param restarted: Denotes whether the DB service should be restarted.
    """
    database_service(restarted=restarted)
    with MariaDB(**db_creds.dict()) as db:
        if not check_for_cellar_db(db_conn=db):
            setup_new_database(db_conn=db)
        if not check_for_admin_user(db_conn=db):
            make_db_admin_user(db_conn=db)
