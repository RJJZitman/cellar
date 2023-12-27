import os
import time
import yaml

from .constants import SRC
from .db_utils import MariaDB
from .models import DbConnModel
from .authentication import get_password_hash


SQL = f'{SRC}sql/'


def database_service() -> None:
    os.system('brew services restart mariadb')
    time.sleep(15)


def setup_new_database(db_conn: MariaDB) -> None:
    print(db_conn.execute_query_select("show databases;"))
    db_conn.execute_query("drop database if exists cellar;")
    print(db_conn.execute_query_select("show databases;"))
    db_conn.execute_sql_file(file_path=f'{SQL}create_databases.sql')
    db_conn.execute_sql_file(file_path=f'{SQL}create_tables.sql',
                             multi=True)
    print(db_conn.execute_query_select("show databases;"))


def make_db_admin_user(db_conn: MariaDB) -> None:
    with open(f'{SRC}env.yml', 'r') as file:
        env = yaml.safe_load(file)

    db_conn.execute_query(query=f"INSERT INTO cellar.owners (username, password, scopes, is_admin, enabled) VALUES"
                                f"({env['DB_USER']}, '{get_password_hash(password=env['DB_PW'])}', '', 1, 1);")


def check_for_cellar_db(db_conn: MariaDB) -> bool:
    existing_dbs = db_conn.execute_query_select("show databases")
    if sum([1 for existing_db in existing_dbs if existing_db[0] == "cellar"]):
        print("cellar DB has been found")
        db_conn.execute_query("use cellar")
        existing_tables = db_conn.execute_query_select("show tables")
        if sum([1 for _ in existing_tables]) < 5:
            print("cellar schema is incomplete and therefore dropped")
            db_conn.execute_query("drop schema cellar")
            return False
        return True
    else:
        return False


def check_for_admin_user(db_conn: MariaDB) -> bool:
    owners = db_conn.execute_query_select(query="SELECT * FROM cellar.owners")
    if owners:
        return True
    else:
        print("No wine owners are found, DB is being re-instantiated")
        return False


def db_setup(db_creds: DbConnModel) -> None:
    database_service()
    with MariaDB(**db_creds.dict()) as db:
        if not check_for_cellar_db(db_conn=db):
            setup_new_database(db_conn=db)
        if not check_for_admin_user(db_conn=db):
            make_db_admin_user(db_conn=db)
