from .db_utils import MariaDB
from .models import DbConnModel


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
        db = MariaDB(**self.db_creds)
        try:
            db._initiate_connection()
            print('DB conn has been established')
            yield db
        finally:
            db._close_connection()
            print('DB conn has been terminated')

