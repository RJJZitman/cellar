from typing import Annotated
from datetime import timedelta, datetime

import jwt

from passlib.context import CryptContext
from fastapi.security import SecurityScopes
from fastapi import Depends, HTTPException, status, Response

from .db_utils import MariaDB
from .auth_utils import OAuth2PasswordBearerCookie
from .models import OwnerDbModel, OwnerModel, TokenData
from .constants import JWT_KEY, ALGORITHM, SCOPES, DB_CONN


pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearerCookie(token_url='users/token', scopes=SCOPES)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain text password equals a hashed password.

    :param plain_password: Plain text password
    :param hashed_password: Hashed password
    :return: whether the provided hash matches the plain pw
    """
    return pwd_context.verify(secret=plain_password, hash=hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plain text password.

    :param password: Plain text password
    :return: Hashed password
    """
    return pwd_context.hash(password)


def verify_scopes(scopes: list[str], user_scopes: str, is_admin: bool = False) -> list[str]:
    """
    Verify for each scope in a list if they are among the allowed scopes for a user. Return only the allowed scopes.
    This check is skipped if the used has admin privileges.

    :param scopes: Requested scopes
    :param user_scopes: Allowed scopes
    :param is_admin: Is the user admin
    :return: list of allowed scopes
    """
    if is_admin:
        return scopes

    return [scope for scope in scopes if scope in user_scopes.split(' ')]


def get_user(username: str, user_db: MariaDB) -> OwnerDbModel | None:
    """
    Get the user information for a user from the database. Return None if the user does not exist.

    :param username: The username to get information for
    :param user_db: The user database connection
    :return: User model or None
    """
    try:
        user = user_db.execute_query_select(query=f"select * from cellar.owners where username='{username}'",
                                            get_fields=True)
        return OwnerDbModel(**user[0])
    except Exception as e:
        print(e)
        return


def authenticate_user(username: str, password: str, user_db: MariaDB) -> OwnerDbModel | bool:
    """
    Authenticate a specified username and password with the database.
    Return the user model if verification is ok, or False.

    :param username: The supplied username
    :param password: The supplied password
    :param user_db: The user database connection
    :return: User model or False
    """
    user = get_user(username=username, user_db=user_db)
    if not user:
        return False
    if not verify_password(plain_password=password, hashed_password=user.password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Encode user and scope data into a JWT access token.

    :param data: User and scope data
    :param expires_delta: How long the token is valid
    :return: JWT access token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(payload=to_encode, key=JWT_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(security_scopes: SecurityScopes, token: Annotated[str, Depends(oauth2_scheme)],
                           user_db: Annotated[MariaDB, Depends(DB_CONN)],
                           response: Response) -> OwnerDbModel:
    """
    Dependency to validate a JWT token. It checks if the token is linked to a valid user and if the token has all the
    scopes needed for the operations that called this dependency. Raise HTTP exception if anything is not valid.

    :param security_scopes: The required scopes.
    :param token: Encoded JWT token.
    :param user_db: User database connection dependency
    :param response: Response
    :return: User model
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = 'Bearer'
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                          detail='Could not validate credentials',
                                          headers={'WWW-Authenticate': authenticate_value})
    try:
        payload = jwt.decode(jwt=token, key=JWT_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_scopes = payload.get('scopes', [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except Exception:
        raise credentials_exception
    user = get_user(username=token_data.username, user_db=user_db)
    if user is None:
        raise credentials_exception
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Not enough permissions',
                                headers={'WWW-Authenticate': authenticate_value})
    response.headers['token_exp'] = str(payload.get('exp'))
    return user


async def get_current_active_user(current_user: Annotated[OwnerModel, Depends(get_current_user)]) -> OwnerModel:
    """
    Dependency to check if the current user is active. This dependency first calls the get_current_user dependency to
    validate the user. Raise HTTP exception if the user is not active.

    :param current_user: dependency for validating the user.
    :return: User model
    """
    if not current_user.enabled:
        raise HTTPException(status_code=400, detail='Inactive user')
    return current_user
