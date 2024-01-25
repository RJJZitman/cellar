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
from ..models import Token, UpdateOwnerModel, OwnerModel, NewOwnerModel


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


@router.get('/get_users', dependencies=[Security(get_current_active_user, scopes=['USERS:WRITE'])])
async def get_users(user_db: Annotated[MariaDB, Depends(DB_CONN)]) -> list[OwnerModel]:
    return user_db.execute_query_select(query="SELECT id, name, username, scopes, is_admin, enabled "
                                              "FROM cellar.owners",
                                        get_fields=True)


@router.post('/add', dependencies=[Security(get_current_active_user, scopes=['USERS:WRITE'])])
async def add_user(user_db: Annotated[MariaDB, Depends(DB_CONN)],
                   owner_data: NewOwnerModel) -> str:
    """
    ADMIN ONLY ENDPOINT
    Add new wine/beer owner to the DB.
    Required scope(s): USERS:READ, USERS:WRITE
    """
    # validate if user exists based on the unique username
    user = user_db.execute_query_select(query="SELECT * FROM cellar.owners WHERE username = %(username)s",
                                        params={"username": owner_data.username})
    if user:
        raise HTTPException(status_code=400, detail=f"A user with username {owner_data.username} already exists")

    # user_db.execute_query(query="INSERT INTO cellar.owners (id, name, username, password, scopes, is_admin, enabled) "
    #                             "VALUES (%(id)s, %(name)s, %(username)s, %(password)s, %(scopes)s, %(is_admin)s, "
    #                             "        %(enabled)s)",
    #                       params={"id": owner_data.id, "name": owner_data.name, "username": owner_data.username,
    user_db.execute_query("INSERT INTO cellar.owners (name, username, password, scopes, is_admin, enabled) "
                          "VALUES (%(name)s, %(username)s, %(password)s, %(scopes)s, %(is_admin)s, "
                          "        %(enabled)s)",
                          params={"name": owner_data.name, "username": owner_data.username,
                                  "password": get_password_hash(password=owner_data.password),
                                  "scopes": owner_data.scopes, "is_admin": owner_data.is_admin,
                                  "enabled": owner_data.enabled})
    return f"User with username {owner_data.username} has successfully been added to the DB"


@router.delete('/delete', dependencies=[Security(get_current_active_user, scopes=['USERS:WRITE'])])
async def delete_user(user_db: Annotated[MariaDB, Depends(DB_CONN)],
                      delete_username: str) -> str:
    """
    ADMIN ONLY ENDPOINT
    Delete existing wine/beer owner to the DB.
    Required scope(s): USERS:READ, USERS:WRITE
    """
    # validate if user exists based on the unique username
    user = user_db.execute_query_select(query="SELECT * FROM cellar.owners WHERE username = %(username)s",
                                        params={"username": delete_username})
    if not user:
        raise HTTPException(status_code=400, detail=f"No users with username {delete_username} exist")
    user_db.execute_query("DELETE FROM cellar.owners WHERE username = %(username)s",
                          params={"username": delete_username})
    return f"User with username {delete_username} has successfully been removed from the DB"


@router.patch('/update', dependencies=[Security(get_current_active_user, scopes=['USERS:WRITE'])])
async def update_user(user_db: Annotated[MariaDB, Depends(DB_CONN)],
                      new_data: UpdateOwnerModel,
                      current_username: str) -> str:
    """
    ADMIN ONLY ENDPOINT
    Updates existing wine/beer owner in the DB.
    Required scope(s): USERS:READ, USERS:WRITE
    """

    # Validate whether the new username exists and if so, if it exists in the DB
    new_user = user_db.execute_query_select(query="SELECT * FROM cellar.owners WHERE username = %(username)s",
                                            params={"username": new_data.username},
                                            get_fields=True)
    if len(new_user) and new_user[0]['username'] != current_username:
        raise HTTPException(status_code=400, detail=f"Users with username {new_user[0]['username']} exist. Please "
                                                    f"provide a unique new username.")

    # Find updated values and construct query string
    update_fields = {}
    for k, v in new_data.dict(exclude_unset=True).items():
        if k == "password":
            # Hash the new password
            update_fields[k] = get_password_hash(v)
        else:
            update_fields[k] = v

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    updated_fields = ", ".join(f"{field} = %({field})s" for field in update_fields)
    user_db.execute_query(f"UPDATE cellar.owners SET {updated_fields} WHERE username = %(current_username)s",
                          params={"current_username": current_username, **update_fields})

    return "User information updated successfully."
