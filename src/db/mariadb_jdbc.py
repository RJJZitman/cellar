from typing import Any
from functools import singledispatchmethod

import pandas as pd
import polars as pl

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.base import Connection
from mysql.connector.cursor import MySQLCursor

from db.jdbc_interface import JdbcDbConn


class JdbcMariaDB(JdbcDbConn):
    """
    DB connector class for a JDBC connection to a MariaDB service.
    """

    def __init__(self, user: str, password: str, database: str, host: str = 'localhost', port: int = 3306) -> None:
        """
        Sets class attributes for further use.

        :param user: JDBC username
        :param password: JDBC password
        :param database: DB schema
        :param host: Hostname of the DB
        :param port: Port over which the connection is made
        """
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.connection: Connection | None = None
        self.cursor: MySQLCursor | None = None

        self.connection_string = f"mysql+mysqlconnector://" \
                                 f"{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    def _initiate_connection(self):
        """
        Connects to the DB engine and initiates a cursor.
        """
        # Use SQLAlchemy to create a connection to MariaDB
        engine = self.engine_connect()
        self.connection = engine.connect()
        self.cursor = self.connection.connection.cursor()

    def _close_connection(self):
        """
        Closes both the DB connection and the cursor.
        """
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def engine_connect(self) -> Engine:
        """
        Constructs a sqlalchemy engine to connect to the DB.
        """
        # Use SQLAlchemy to create a MariaDB engine
        engine = create_engine(self.connection_string)
        return engine

    @singledispatchmethod
    def execute_query(self, query, params: dict[str, Any] | list | tuple | None = None) -> None:

        """
        Executes a single query. Uses a transaction to commit the executed query automatically.
        Make sure to provide the query as the first positional argument without a keyword.

        :param query: The query that is executed
        :param params: Optional extra query params
        """
        raise NotImplementedError(f"Only allows types [list, str] for the 'query' parameter. Got {type(query)}")

    @execute_query.register
    def _(self, query: str, params: dict[str, Any] | list | tuple | None = None) -> None:
        """
        Executes a single query. Uses a transaction to commit the executed query automatically.
        Make sure to provide the query as the first positional argument without a keyword.

        :param query: The query that is executed
        :param params: Optional extra query params
        """
        with self.connection.begin() as trans:
            self.cursor.execute(operation=query, params=params)

    @execute_query.register
    def _(self, query: list, params: dict[str, Any] | list | tuple | None = None) -> None:
        """
        Executes multiple queries provided as a list of query strings

        :param query: The list of queries to be executed
        :param params: Optional extra query params
        """
        if params is None:
            params = len(query) * [None]
        if len(params) != len(query):
            raise ValueError("Number of parameters does not match the number of queries.")

        for q, param in zip(query, params):
            self.execute_query(q, params=param)

    def execute_query_select(self, query: str, params: dict[str, Any] | list | tuple | None = None,
                             get_fields: bool = False) -> Any:
        """
        Executes a select query.

        :param query: The executed select query
        :param params: Optional extra query params
        :param get_fields: Denotes whether the field names should be retrieved
        :return: The data requested by the query
        """
        self.cursor.execute(operation=query, params=params)
        result = self.cursor.fetchall()
        if get_fields:
            cols = self.cursor.column_names
            result = [{col: value for col, value in zip(cols, row)} for row in result]
        return result

    def read_table(self, table: str) -> Any:
        return self.execute_query_select(query="SELECT * FROM %(table)s", params={'table': table})

    @singledispatchmethod
    def create_records(self, data, table: list[str] | str | None) -> None:
        raise NotImplementedError(f"Only allows types [pd.DataFrame, pl.DataFrame] for the 'data' parameter. "
                                  f"Got {type(data)}")

    @create_records.register
    def _(self, data: dict | list, table: str) -> None:
        raise NotImplementedError("Main priority to add, not implemented yet. Convert to pandas or polars df for now.")

    @create_records.register
    def _(self, data: pd.DataFrame, table: str) -> None:
        data.to_sql(name=table, con=self.engine_connect(), if_exists='append')

    @create_records.register
    def _(self, data: pl.DataFrame, table: str) -> None:
        data.write_database(name=table, connection=self.connection_string, if_table_exists='append')

    def update(self, data, table: str, pk_field: str, pk_val: Any, **kwargs) -> None:
        update_query = (f"UPDATE %(table)s "
                        f"SET {', '.join([f'{k} = %({k}))s' for k in data.keys()])} "
                        f"WHERE %(pk_field)s = %(pk_val)s")
        self.execute_query(update_query, params=dict(data, **{'pk_field': pk_field, 'pk_val': pk_val}))

    def record_exists(self, table: str, pk_field: str, pk_val: Any, **kwargs) -> Any | bool:
        record = self.execute_query_select(query="SELECT %(pk_field)s FROM %(table)s WHERE %(pk_field)s = %(pk_val)s",
                                           params={'pk_field': pk_field, 'pk_val': pk_val})
        return record if len(record) else False

    def delete(self, table: str, pk_field: str, pk_val: Any) -> Any:
        if record := self.record_exists(table=table, pk_field=pk_field, pk_val=pk_val):
            self.execute_query("DELETE FROM %(table)s WHERE %(pk_field)s = %(pk_val)s ",
                               params={'table': table, 'pk_field': pk_field, 'pk_val': pk_val})
            return record
        else:
            return IndexError(f"Record in table {table} with PK ({pk_field}) = {pk_val} could not be deleted, because "
                              f"it does not exist.")
