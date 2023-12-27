import os
import yaml
import base64

from typing import Annotated
from datetime import datetime, timedelta, timezone

import fastapi.openapi.utils
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi_pagination import add_pagination
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import RedirectResponse, Response

from .db_utils import MariaDB
from .auth_utils import BasicAuth
from .db_initialisation import db_setup
from .constants import ACCESS_TOKEN_EXPIRATION_MIN, OPENAPI_URL, SRC
from .authentication import auth_db_conn, get_current_active_user, authenticate_user, create_access_token
from .get_request_body_with_explode import get_request_body_with_explode
from .models import DbConnModel


# Monkeypatch to fix swagger UI bug: https://github.com/tiangolo/fastapi/issues/3532
fastapi.openapi.utils.get_openapi_operation_request_body = get_request_body_with_explode

app = FastAPI(title='Wine Cellar API',
              description='API to access your wine cellar data',
              version="0.1.0",
              docs_url=None, redoc_url=None, openapi_url=OPENAPI_URL)
add_pagination(app)

with open(f'{SRC}env.yml', 'r') as file:
    env = yaml.safe_load(file)
db_setup(db_creds=DbConnModel(user=env['DB_USER'], password=env['DB_PW']))
basic_auth = BasicAuth(auto_error=False)


@app.get('/')
async def root():
    return {"message": "Welcome to the wine API."}


@app.get("/login", include_in_schema=False)
async def login_for_docs(auth: Annotated[BasicAuth, Depends(basic_auth)],
                         user_db: Annotated[MariaDB, Depends(auth_db_conn)]):
    if not auth:
        return Response(headers={"WWW-Authenticate": "Basic"}, status_code=401)
    try:
        decoded = base64.b64decode(auth).decode("ascii")
        username, _, password = decoded.partition(":")
        user = authenticate_user(username=username, password=password, user_db=user_db)
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRATION_MIN)
        access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)

        response = RedirectResponse(url="/docs")
        response.set_cookie(key="Authorization",
                            value=f"Bearer {jsonable_encoder(access_token)}",
                            httponly=True,
                            expires=datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRATION_MIN))
        return response
    except Exception as e:
        response = Response(headers={"WWW-Authenticate": "Basic"}, status_code=401)
        return response


@app.get("/docs", dependencies=[Depends(get_current_active_user)], include_in_schema=False)
async def get_documentation(request: Request):
    root_path = request.scope.get("root_path", "").rstrip("/")
    return get_swagger_ui_html(openapi_url=f"{root_path}{OPENAPI_URL}", title="docs")
