from typing import Any
from abc import ABCMeta, abstractmethod


class JdbcDbConn(metaclass=ABCMeta):
    """
    Interface for DB connector classes connecting to a DB service via a JDBC connection.
    """

    def __call__(self):
        return self

    def __enter__(self):
        """
        Context manager to initiate the DB connection.
        """
        self._initiate_connection()
        return self

    def __exit__(self, *exc_info):
        """
        Context manager to close the DB connection.
        """
        self._close_connection()

    @abstractmethod
    def _initiate_connection(self):
        """
        Connects to the DB engine and initiates a cursor.
        """
        pass

    @abstractmethod
    def _close_connection(self):
        """
        Closes both the DB connection and the cursor.
        """
        pass

    @abstractmethod
    def execute_query(self, query: Any, params: dict[str, Any] | list | tuple | None = None) -> None:

        """
        Executes a single query.
        Make sure to provide the query as the first positional argument without a keyword.

        :param query: The query that is executed
        :param params: Optional extra query params
        """
        pass

    @abstractmethod
    def execute_query_select(self, query: str, params: dict[str, Any] | list | tuple | None = None,
                             get_fields: bool = False) -> Any:
        """
        Executes a select query.

        :param query: The executed select query
        :param params: Optional extra query params
        :param get_fields: Denotes whether the field names should be retrieved
        :return: The data requested by the query
        """
        pass

    @abstractmethod
    def read_table(self, table: str) -> Any:
        pass

    @abstractmethod
    def create_records(self, data: list[dict] | dict, table: list[str] | str | None) -> None:
        pass

    @abstractmethod
    def record_exists(self, table: str, pk_field: str, pk_val: Any, **kwargs) -> bool:
        pass

    @abstractmethod
    def update(self, data, table: str, pk_field: str, pk_val: Any, **kwargs) -> None:
        pass

    @abstractmethod
    def delete(self, table: str, pk_field: str, pk_val: Any) -> None:
        pass

    def execute_sql_file(self, file_path: str, params: dict[str, Any] | list | tuple | None = None) -> None:
        """
        Reads a SQL string from a file and executes the query. Note that this method only support non-select queries.

        :param file_path: path to where the query-containing file lives
        :param params: Optional extra query params
        """
        with open(file=file_path, mode='r') as sql_file:
            queries = sql_file.read().split(';')[:-1]

        if len(queries) == 1:
            queries = queries[0]
        elif len(queries) < 1:
            raise ValueError("No queries found in the SQL file.")
        self.execute_query(queries, params=params)

    def upsert(self, data: dict, table: str, pk_field: str, pk_val: Any) -> None:
        if self.record_exists(table=table, pk_field=pk_field, pk_val=pk_val):
            self.update(data=data, table=table, pk_field=pk_field, key_val=pk_val)
        else:
            self.create_records(data, table=table)
