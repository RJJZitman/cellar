import yaml

OPENAPI_URL = f"/drink_your_wine"
SRC = '/Users/Lenna_C02ZL0UYLVDT/Weekeinden/cellar/src/'

# Authorization
with open(f'{SRC}env.yml', 'r') as file:
    env = yaml.safe_load(file)
JWT_KEY = env['JWT_KEY']
ALGORITHM = env['JWT_ALGORITHM']
ACCESS_TOKEN_EXPIRATION_MIN = env['ACCESS_TOKEN_EXPIRATION_MIN']

SCOPES = {'test:read': 'test scope'}
