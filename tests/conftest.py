import os
import json

from typing import Any

import pytest

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from fastapi_pagination import add_pagination


from api import dependencies, db_initialisation, db_utils, constants

SQLITE_DB_URL = 'sqlite://'


@pytest.fixture()
def test_app():
    from api.main import app
    add_pagination(app)
    client = TestClient(app)
    yield client


@pytest.fixture()
def token_admin(test_app):
    response = test_app.post(url='/users/token', data={'username': 'admin',
                                                       'password': 'admin',
                                                       'scope': 'USERS:READ USERS:WRITE'},
                             headers={"content-type": "application/x-www-form-urlencoded"})
    return response.json()


@pytest.fixture()
def new_user(test_app):
    def set_user_scopes(data: dict, token: dict):
        test_app.post(url='/users/add',
                      data=json.dumps(data),
                      headers={"content-type": "application/json",
                               "Authorization": f"Bearer {token['access_token']}"})
    return set_user_scopes


@pytest.fixture()
def token_cellar_read(test_app, new_user, token_admin):
    def get_token(data: dict):
        token = token_admin
        new_user(data=data, token=token)
        response = test_app.post(url='/users/token', data={'username': data['username'],
                                                           'password': data['password'],
                                                           'scope': data['scopes']},
                                 headers={"content-type": "application/x-www-form-urlencoded"})
        return response.json()

    return get_token


@pytest.fixture()
def token_cellar_all(test_app):
    response = test_app.post(url='/users/token', data={'username': 'cellar_all',
                                                       'password': 'cellar_all',
                                                       'scope': 'CELLAR:READ CELLAR:WRITE'},
                             headers={"content-type": "application/x-www-form-urlencoded"})
    return response.json()


@pytest.fixture()
def token_nothing(test_app):
    response = test_app.post(url='/users/token', data={'username': 'nothing',
                                                       'password': 'nothing',
                                                       'scope': ''},
                             headers={"content-type": "application/x-www-form-urlencoded"})
    return response.json()


@pytest.fixture(scope='session', autouse=True)
def in_memory_db_conn():
    engine = create_engine(SQLITE_DB_URL, connect_args={'check_same_thread': False}, poolclass=StaticPool)
    yield engine


@pytest.fixture(autouse=True)
def env_monkeypatch(monkeypatch):
    monkeypatch.setattr(constants, 'SRC', '/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/tests/test_')
    monkeypatch.setattr(db_initialisation, 'SRC', '/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/tests/test_')


@pytest.fixture(autouse=True)
def db_monkeypatch(in_memory_db_conn, monkeypatch):
    class MockMariaDB:
        def __init__(self, *args, **kwargs):
            self.conn = in_memory_db_conn
            for k, v in kwargs.items():
                setattr(self, k, v)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            pass

        def _alter_query(self, query: str) -> str:
            query = (query.replace('AUTO_INCREMENT', '')
                     .replace(')s', '')
                     .replace('%(', ':')
                     .replace('cellar.', '')
                     .replace('NOT NULL', ''))

            # make sure to insert a unique id when initializing the db
            if 'INSERT INTO owners (name' in query:
                ids = self.execute_query_select("select id from owners")
                if ids:
                    max_id = max([id[0] for id in ids])
                else:
                    max_id = 0
                query = (query.replace('INSERT INTO owners (name', 'INSERT INTO owners (id, name')
                         .replace('VALUES (', f'VALUES ({max_id}, '))
            return query

        def execute_query_select(self, query: str, params: dict[str, Any] | list | tuple | None = None,
                                 get_fields: bool = False):
            if params is None:
                params = {}
            cursor = self.conn.execute(self._alter_query(query), params)
            result = cursor.fetchall()
            if get_fields:
                cols = [key for key in cursor.keys()]
                result = [{col: value for col, value in zip(cols, row)} for row in result]

            return result

        def execute_query(self, query: str, params: dict[str, Any] | list | tuple | None = None):
            if params is None:
                params = {}
            if 'SCHEMA' in query:
                return
            elif ' database if ' in query.lower():
                return False
            self.conn.execute(self._alter_query(query), params)

        def execute_sql_file(self, file_path: str, multi: bool = False) -> None:
            with open(file=file_path, mode='r') as sql_file:
                if multi:
                    self.execute_queries(queries=sql_file.read())
                else:
                    self.execute_query(query=sql_file.read())

        def execute_queries(self, queries: str) -> None:
            for query in queries.split(';')[:-1]:
                print(query)
                self.execute_query(query=f"{query};")

        def _initiate_connection(self):
            pass

        def _close_connection(self):
            pass

    def mock_database_service(*args, **kwargs):
        pass

    def mock_check_for_admin_user(*args, **kwargs):
        return False

    def mock_check_for_cellar_db(*args, **kwargs):
        return False

    monkeypatch.setattr(db_utils, 'MariaDB', MockMariaDB)
    monkeypatch.setattr(dependencies, 'MariaDB', MockMariaDB)
    monkeypatch.setattr(db_initialisation, 'MariaDB', MockMariaDB)
    monkeypatch.setattr(db_initialisation, 'database_service', mock_database_service)
    monkeypatch.setattr(db_initialisation, 'check_for_cellar_db', mock_check_for_cellar_db)
    monkeypatch.setattr(db_initialisation, 'check_for_admin_user', mock_check_for_admin_user)

