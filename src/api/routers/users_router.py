from enum import Enum
from typing import Annotated
from datetime import timedelta

from fastapi import HTTPException, status
from fastapi import APIRouter, Depends, Security, Form
from fastapi.security import OAuth2PasswordRequestForm

from ..db_utils import MariaDB
from ..constants import ACCESS_TOKEN_EXPIRATION_MIN, SCOPES, DB_CONN
from ..authentication import (authenticate_user, create_access_token, verify_scopes, get_password_hash,
                              get_current_active_user, get_user)
from ..models import Token, OwnerDbModel


SCOPES_ENUM = Enum('ScopesType', ((s, s) for s in SCOPES.keys()), type=str)

router = APIRouter(prefix="/users",
                   tags=["users"],
                   responses={404: {"description": "Not Found"}})


@router.post(path='/token', response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 user_db: Annotated[MariaDB, Depends(DB_CONN)]):
    f"""
    Login form for Oauth2. Validates credentials, verifies permissions and generates an access token with only 
    the specified scopes that this user has access to. Tokens are valid for {ACCESS_TOKEN_EXPIRATION_MIN} minutes. This
    endpoint is designed to serve as login function for debugging on the swagger UI.
    Required scope(s): None
    """
    user = authenticate_user(username=form_data.username, password=form_data.password, user_db=user_db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Incorrect username or password',
                            headers={'WWW-Authenticate': 'Bearer'})

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRATION_MIN)
    access_token = create_access_token(
        data={'sub': user.username, 'scopes': verify_scopes(scopes=form_data.scopes, user_scopes=user.scopes,
                                                            is_admin=user.is_admin)},
        expires_delta=access_token_expires
    )
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post(path='/extendedtoken', response_model=Token,
             dependencies=[Security(get_current_active_user, scopes=['USERS:WRITE'])])
async def get_extended_access_token(user_db: Annotated[MariaDB, Depends(DB_CONN)],
                                    token_user: Annotated[str, Form()],
                                    scopes: Annotated[list[SCOPES_ENUM], Form()],
                                    days_valid: Annotated[int, Form(..., ge=1, le=365)]):
    """
    ADMIN ONLY ENDPOINT
    Generate an access token with extended expiration date of up to a year. The token can be generated for any user in
    the database. Only scopes that the intended user is allowed to use can be added to this token.
    Required scope(s): USERS:READ, USERS:WRITE
    """
    token_user_model = get_user(username=token_user, user_db=user_db)
    if not token_user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'User {token_user} does not exist.')
    access_token_expires = timedelta(days=days_valid)
    access_token = create_access_token(data={'sub': token_user_model.username,
                                             'scopes': verify_scopes(scopes=[str(s.value) for s in scopes],
                                                                     user_scopes=token_user_model.scopes,
                                                                     is_admin=token_user_model.is_admin)},
                                       expires_delta=access_token_expires)

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/add', dependencies=[Security(get_current_active_user, scopes=['USERS:WRITE'])])
async def add_user(user_db: Annotated[MariaDB, Depends(DB_CONN)],
                   owner_data: OwnerDbModel) -> str:
    """
    ADMIN ONLY ENDPOINT
    Add new wine/beer owner to the DB.
    Required scope(s): USERS:READ, USERS:WRITE
    """
    # validate if user exists based on the unique username
    user = user_db.execute_query_select(query="SELECT * FROM cellar.owners WHERE username = :username",
                                        params={"username": owner_data.username})
    if user:
        raise HTTPException(status_code=400, detail=f"A user with username {owner_data.username} already exists")
    user_db.execute_query(query=f"INSERT INTO cellar.owners (id, name, username, password, scopes, is_admin, enabled) "
                                f"VALUES "
                                f"(:id,:name, :username, :password, :scopes, :is_admin, :enabled)",
                          params={"id": owner_data.id, "name": owner_data.name, "username": owner_data.username,
                                  "password": get_password_hash(password=owner_data.password),
                                  "scopes": owner_data.scopes, "is_admin": owner_data.is_admin,
                                  "enabled": owner_data.enabled})
    return f"User with username {owner_data.username} has successfully been added to the DB"
