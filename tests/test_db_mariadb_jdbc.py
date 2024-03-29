from typing import Any

import pytest

from db import mariadb_jdbc


@pytest.fixture
def sqlalchemy_monkeypatch(monkeypatch):
    def mock_create_engine(*args, **kwargs):

        class MockEngine:
            def __init__(self):
                self.created = True

            def connect(self):
                class MockConnection:
                    def __init__(self):
                        self.connection_init = True

                        class MockConn:
                            def __init__(self):
                                pass

                            def cursor(self):
                                class MockCursor:
                                    def __init__(self):
                                        self.cursor_init = True
                                        self.column_names = ["a", "b"]

                                    def execute(self, operation: str, params: Any):
                                        if operation == "exception":
                                            raise Exception("MOCK EXCEPTION CURSOR EXECUTE")

                                    def fetchall(self):
                                        return [(1, 2), (3, 4)]

                                    def close(self):
                                        self.cursor_init = False
                                return MockCursor()
                        self.connection = MockConn()

                    def close(self):
                        self.connection_init = False

                    def begin(self):
                        class MockTransaction:
                            def __init__(self):
                                pass

                            def __enter__(self, *args, **kwargs):
                                return self

                            def __exit__(self, *exc_info):
                                pass
                        return MockTransaction()
                return MockConnection()

        return MockEngine()

    monkeypatch.setattr(mariadb_jdbc, 'create_engine', mock_create_engine)


@pytest.mark.unit
@pytest.mark.usefixtures("sqlalchemy_monkeypatch")
class TestJdbcMariaDB:
    basic_init = {"user": "basic", "password": "basic", "database": "basic"}

    def test_init(self):
        db = mariadb_jdbc.JdbcMariaDB(**self.basic_init)

        assert db.connection_string == "mysql+mysqlconnector://basic:basic@localhost:3306/basic"

    def test_engine_connect(self):
        db = mariadb_jdbc.JdbcMariaDB(**self.basic_init)
        assert db.engine_connect().created

    def test_initiate_connection(self):
        db = mariadb_jdbc.JdbcMariaDB(**self.basic_init)
        db._initiate_connection()
        assert db.connection.connection_init
        assert db.cursor.cursor_init

    def test_close_connection(self):
        db = mariadb_jdbc.JdbcMariaDB(**self.basic_init)
        db._initiate_connection()
        db._close_connection()
        assert not db.connection.connection_init
        assert not db.cursor.cursor_init

    def test_enter_exit(self):
        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            assert db.connection.connection_init
            assert db.cursor.cursor_init
        assert not db.connection.connection_init
        assert not db.cursor.cursor_init

    def test_execute_query(self):
        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            with pytest.raises(Exception) as e_info:
                db.execute_query("exception")
            assert str(e_info.value) == "MOCK EXCEPTION CURSOR EXECUTE"

    def test_execute_queries(self):
        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            db.execute_query(["hello", "bye"])

    def test_execute_queries_params(self):
        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            db.execute_query(["hello", "bye"], params=[{"a": 1}, {"b": 2}])

    def test_execute_queries_params_non_matching_nb_params(self):
        with pytest.raises(ValueError):
            with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
                db.execute_query(["hello", "bye"], params=[{"a": 1}, {"b": 2}, {"c": 3}])

    def test_execute_query_select_no_fields(self):
        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            result = db.execute_query_select(query="select test query", get_fields=False)

        assert result == [(1, 2), (3, 4)]

    def test_execute_query_select_with_fields(self):
        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            result = db.execute_query_select(query="select test query", get_fields=True)

        assert result == [{"a": 1, "b": 2}, {"a": 3, "b": 4}]

    def test_execute_sql_file_multiple_queries(self, tmp_path):
        file_path = tmp_path / "q.sql"
        file_path.touch()
        file_path.write_text("hello;bey;")

        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            db.execute_sql_file(file_path=str(file_path))

    def test_execute_sql_file_single_query(self, tmp_path):
        file_path = tmp_path / "q.sql"
        file_path.touch()
        file_path.write_text("hello;")

        with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
            db.execute_sql_file(file_path=str(file_path))

    def test_execute_sql_file_no_query(self, tmp_path):
        file_path = tmp_path / "q.sql"
        file_path.touch()
        file_path.write_text("hello")

        with pytest.raises(ValueError):
            with mariadb_jdbc.JdbcMariaDB(**self.basic_init) as db:
                db.execute_sql_file(file_path=str(file_path))
