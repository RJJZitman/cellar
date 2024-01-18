import pytest

from datetime import timedelta

from api import authentication


@pytest.fixture
def pwd_context():
    return authentication.CryptContext(schemes=['bcrypt'], deprecated='auto')


@pytest.mark.unit
def test_verify_password(pwd_context):
    pw = 'pw'
    pw_hash = pwd_context.hash(pw)

    assert authentication.verify_password(plain_password=pw, hashed_password=pw_hash)


@pytest.mark.unit
def test_get_password_hash(pwd_context):
    pw = 'pw'
    pw_hash = authentication.get_password_hash(password=pw)

    assert authentication.verify_password(plain_password=pw, hashed_password=pw_hash)


@pytest.mark.unit
@pytest.mark.parametrize("user_scopes, is_admin", [("A B C", False), ("A B C", True)])
def test_verify_scopes(user_scopes, is_admin):
    scopes = ["A", "B", "C", "D"]
    result = authentication.verify_scopes(scopes=scopes, user_scopes=user_scopes, is_admin=is_admin)
    if is_admin:
        assert result == scopes
    else:
        assert result == user_scopes.split(" ")


@pytest.mark.unit
def test_get_user_exists(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    result = authentication.get_user(username='admin', user_db=db_test_conn)

    assert result.username == 'admin'
    assert result.id == 0


@pytest.mark.unit
def test_get_user_not_exists(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    result = authentication.get_user(username='not_a_user', user_db=db_test_conn)

    assert not result


@pytest.mark.unit
def test_authenticate_user(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    result = authentication.authenticate_user(username='admin', password='admin', user_db=db_test_conn)

    assert result.username == 'admin'
    assert result.id == 0


@pytest.mark.unit
def test_authenticate_user_wrong_pw(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    result = authentication.authenticate_user(username='admin', password='', user_db=db_test_conn)

    assert not result


@pytest.mark.unit
def test_authenticate_user_not_exists(test_app, db_monkeypatch):
    db_test_conn = db_monkeypatch
    result = authentication.authenticate_user(username='not_a_user', password='', user_db=db_test_conn)

    assert not result


@pytest.mark.unit
@pytest.mark.parametrize("expires_delta", [None, timedelta(minutes=1)])
def test_create_access_token(expires_delta):
    data = {"a": 1, "b": 2}
    result = authentication.create_access_token(data=data, expires_delta=expires_delta)
    decoded = authentication.jwt.decode(jwt=result, key=authentication.JWT_KEY, algorithms=[authentication.ALGORITHM])

    assert decoded['a'] == 1
    assert decoded['b'] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("scopes", [["CELLAR:READ"], None])
async def test_get_current_user(scopes, test_app, db_monkeypatch, token_new_user, cellar_all_user_data):
    security_scopes = authentication.SecurityScopes(scopes=scopes)
    token = token_new_user(data=cellar_all_user_data)
    db_conn = db_monkeypatch
    resp = authentication.Response()

    result = await authentication.get_current_user(security_scopes=security_scopes,
                                                   token=token['access_token'],
                                                   user_db=db_conn,
                                                   response=resp)
    result = result.dict()
    del result['password']
    del cellar_all_user_data['password']
    assert result['username'] == cellar_all_user_data['username']
    assert result == cellar_all_user_data


@pytest.mark.asyncio
async def test_get_current_user_unauthorized_scopes(test_app, db_monkeypatch, token_new_user, cellar_all_user_data):
    security_scopes = authentication.SecurityScopes(scopes=["A"])
    token = token_new_user(data=cellar_all_user_data)
    db_conn = db_monkeypatch
    resp = authentication.Response()

    with pytest.raises(authentication.HTTPException):
        result = await authentication.get_current_user(security_scopes=security_scopes,
                                                       token=token['access_token'],
                                                       user_db=db_conn,
                                                       response=resp)


@pytest.mark.asyncio
async def test_get_current_user_unauthorized_username(test_app, db_monkeypatch, token_new_user, cellar_all_user_data):
    security_scopes = authentication.SecurityScopes(scopes=["CELLAR:READ"])
    resp = authentication.Response()

    # get token and change username to None to test if statement checking presence of a username
    token = token_new_user(data=cellar_all_user_data)
    token = authentication.jwt.decode(jwt=token['access_token'], key=authentication.JWT_KEY, algorithms=[authentication.ALGORITHM])
    token['sub'] = None
    token = authentication.jwt.encode(payload=token, key=authentication.JWT_KEY, algorithm=authentication.ALGORITHM)
    db_conn = db_monkeypatch

    with pytest.raises(authentication.HTTPException):
        result = await authentication.get_current_user(security_scopes=security_scopes,
                                                       token=token,
                                                       user_db=db_conn,
                                                       response=resp)


@pytest.mark.asyncio
async def test_get_current_user_not_exists(test_app, db_monkeypatch, token_new_user, cellar_all_user_data):
    security_scopes = authentication.SecurityScopes(scopes=["CELLAR:READ"])
    resp = authentication.Response()

    # get token and change username to a non-existing username to test if statement checking presence of a existing user
    token = token_new_user(data=cellar_all_user_data)
    token = authentication.jwt.decode(jwt=token['access_token'], key=authentication.JWT_KEY, algorithms=[authentication.ALGORITHM])
    token['sub'] = 'non_existing_user'
    token = authentication.jwt.encode(payload=token, key=authentication.JWT_KEY, algorithm=authentication.ALGORITHM)
    db_conn = db_monkeypatch

    with pytest.raises(authentication.HTTPException):
        result = await authentication.get_current_user(security_scopes=security_scopes,
                                                       token=token,
                                                       user_db=db_conn,
                                                       response=resp)


@pytest.mark.asyncio
async def test_get_current_active_user(test_app, db_monkeypatch, token_new_user, cellar_all_user_data):
    user = authentication.OwnerModel(**cellar_all_user_data)
    result = await authentication.get_current_active_user(current_user=user)

    assert result == user


@pytest.mark.asyncio
async def test_get_current_active_user(test_app, db_monkeypatch, token_new_user, inactive_user_data):
    user = authentication.OwnerModel(**inactive_user_data)

    with pytest.raises(authentication.HTTPException):
        result = await authentication.get_current_active_user(current_user=user)
