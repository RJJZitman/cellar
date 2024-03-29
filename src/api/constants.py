import yaml

from .models import DbConnModel
from .dependencies import DBConnDep


OPENAPI_URL = f"/drink_your_wine"
SRC = 'src/'
SQL = f'{SRC}sql/'

# Authorization & DB
with open(f'{SRC}env.yml', 'r') as file:
    env = yaml.safe_load(file)
DB_CREDS = DbConnModel(user=env['DB_USER'], password=env['DB_PW'])
DB_CONN = DBConnDep(db_creds=DB_CREDS)
SETUP_DB = False

JWT_KEY = env['JWT_KEY']
ALGORITHM = env['JWT_ALGORITHM']
ACCESS_TOKEN_EXPIRATION_MIN = env['ACCESS_TOKEN_EXPIRATION_MIN']


SCOPES = {'USERS:WRITE': 'allows writes on users router scope',
          'USERS:READ': 'allows reads on users router scope',
          'CELLAR:WRITE': 'allows writes on cellar router scope',
          'CELLAR:READ': 'allows reads on cellar router scope'
          }
