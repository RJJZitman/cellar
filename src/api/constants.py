import yaml

from .models import DbConnModel

OPENAPI_URL = f"/drink_your_wine"
SRC = '/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/src/'
SQL = f'{SRC}sql/'

# Authorization
with open(f'{SRC}env.yml', 'r') as file:
    env = yaml.safe_load(file)
JWT_KEY = env['JWT_KEY']
ALGORITHM = env['JWT_ALGORITHM']
ACCESS_TOKEN_EXPIRATION_MIN = env['ACCESS_TOKEN_EXPIRATION_MIN']

DB_CREDS = DbConnModel(user=env['DB_USER'], password=env['DB_PW'])

SCOPES = {'USERS:WRITE': 'allows writes on users router scope',
          'USERS:READ': 'allows reads on users router scope'}
