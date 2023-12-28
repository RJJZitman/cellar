from .db_utils import MariaDB
from .models import DbConnModel


class DBConnDep:
    def __init__(self, db_creds: DbConnModel):
        self.db_creds = db_creds.dict()

    def __call__(self):
        db = MariaDB(**self.db_creds)
        try:
            db._initiate_connection()
            print('DB conn has been established')
            yield db
        finally:
            db._close_connection()
            print('DB conn has been terminated')

