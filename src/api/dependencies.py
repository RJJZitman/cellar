from .db_utils import MariaDB
from .models import DbConnModel


class DBConnDep:
    def __init__(self, db_creds: DbConnModel):
        self.db_creds = db_creds.dict()

    def __call__(self):
        with MariaDB(**self.db_creds) as db:
            print('DB conn has been established')
            yield db
            print('DB conn has been terminated')
