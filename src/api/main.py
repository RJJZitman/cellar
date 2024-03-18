import yaml
import base64

from typing import Annotated
from datetime import datetime, timedelta, timezone

import fastapi.openapi.utils

from fastapi.encoders import jsonable_encoder
from fastapi_pagination import add_pagination
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import RedirectResponse, Response
from fastapi import FastAPI, Depends, HTTPException, Request

from db.jdbc_interface import JdbcDbConn

from .auth_utils import BasicAuth
from .db_initialisation import db_setup
from .routers import users_router, cellar_router, cellar_views_router
from .constants import ACCESS_TOKEN_EXPIRATION_MIN, OPENAPI_URL, SRC, DB_CREDS, DB_CONN
from .authentication import get_current_active_user, authenticate_user, create_access_token

from .get_request_body_with_explode import get_request_body_with_explode


# Monkeypatch to fix swagger UI bug: https://github.com/tiangolo/fastapi/issues/3532
fastapi.openapi.utils.get_openapi_operation_request_body = get_request_body_with_explode

app = FastAPI(title='Wine Cellar API',
              description='API to access your wine and beer cellar',
              version="0.1.0",
              docs_url=None, redoc_url=None, openapi_url=OPENAPI_URL)
add_pagination(app)

with open(f'{SRC}env.yml', 'r') as file:
    env = yaml.safe_load(file)
db_setup(db_creds=DB_CREDS, restarted=False)
basic_auth = BasicAuth(auto_error=False)

app.include_router(users_router.router)
app.include_router(cellar_router.router)
app.include_router(cellar_views_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "https://rjjzitman.github.io/cellar/"],  # Allow requests from any origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get('/', include_in_schema=False)
async def root():
    return {"message": "Welcome to the wine API. Go to /login to access the swaggerUI"}


@app.get("/login", include_in_schema=False)
async def login_for_docs(auth: Annotated[BasicAuth, Depends(basic_auth)],
                         db_conn: Annotated[JdbcDbConn, Depends(DB_CONN)]):
    """
    Endpoint used to access the swagger UI. This endpoint is only called in the WebBrowser and for debugging
    purposes only.
    Required scope(s): None

    :param auth: Authorisation form
    :param db_conn: Dependency yielding a live DB connection
    """
    if not auth:
        return Response(headers={"WWW-Authenticate": "Basic"}, status_code=401)
    try:
        dec_auth = base64.b64decode(auth).decode("ascii")
        username, _, pw = dec_auth.partition(":")
        user = authenticate_user(username=username, password=pw, user_db=db_conn)
        print("user is found")
        if not user:
            raise HTTPException(status_code=400, detail="Incorrect login credentials")
        access_token_exp = timedelta(minutes=ACCESS_TOKEN_EXPIRATION_MIN)
        access_token = create_access_token(data={"sub": username}, expires_delta=access_token_exp)

        response = RedirectResponse(url="/docs")
        response.set_cookie(key="Authorization",
                            value=f"Bearer {jsonable_encoder(access_token)}",
                            httponly=True,
                            expires=datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRATION_MIN))
        return response
    except Exception as e:
        print(e)
        response = Response(headers={"WWW-Authenticate": "Basic"}, status_code=401, content="Invalid login")
        return response


@app.get("/docs", dependencies=[Depends(get_current_active_user)], include_in_schema=False)
async def get_documentation(request: Request):
    """
    Sets up the swagger UI. Should only be called by the /login page.

    Required scope(s): None
    """
    root_path = request.scope.get("root_path", "").rstrip("/")
    return get_swagger_ui_html(openapi_url=f"{root_path}{OPENAPI_URL}", title="docs")
