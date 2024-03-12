from db.mariadb_jdbc import JdbcMariaDB
from db.jdbc_interface import JdbcDbConn
from .models import DbConnModel
from typing import Type


# class DBConnDep:
#     """
#     Dependency which yields a DB connection to use in endpoints.
#     """
#     def __init__(self, db_creds: DbConnModel, db_conn_class: Type[JdbcDbConn]):
#         """
#         Sets class attributes.
#
#         :param db_creds: Credentials for the DB connection
#         :param db_conn_class: Class for the DB connection
#         """
#         self.db_creds = db_creds.dict()
#         self.db_conn_class = db_conn_class
#
#     def __call__(self):
#         """
#         Instantiates the database connection class and yields a live connection.
#         """
#         db = self.db_conn_class(**self.db_creds)
#         try:
#             db._initiate_connection()
#             print('DB conn has been established')
#             yield db
#         finally:
#             db._close_connection()
#             print('DB conn has been terminated')


class DBConnDep:
    """
    Dependency which yields a DB connection to use in endpoints.
    """
    def __init__(self, db_creds: DbConnModel):
        """
        Sets class attributes.

        :param db_creds: Credentials for the DB connection
        """
        self.db_creds = db_creds.dict()

    def __call__(self):
        """
        Instantiates the MariaDB class and yield a live connection which is always closed in the 'finally' block.
        """
        db = JdbcMariaDB(**self.db_creds)
        try:
            db._initiate_connection()
            print('DB conn has been established')
            yield db
        finally:
            db._close_connection()
            print('DB conn has been terminated')

