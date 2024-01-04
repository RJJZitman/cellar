import pytest

from api import db_initialisation


@pytest.fixture
def os_monkeypatch(monkeypatch):
    def mock_os_system(*args, **kwargs):
        pass

    monkeypatch.setattr(db_initialisation.os, 'system', mock_os_system)


@pytest.fixture
def time_monkeypatch(monkeypatch):
    def mock_time_sleep(*args, **kwargs):
        pass

    monkeypatch.setattr(db_initialisation.time, 'sleep', mock_time_sleep)


@pytest.mark.unit
@pytest.mark.parametrize("restarted", [True, False])
def test_database_service(restarted, os_monkeypatch, time_monkeypatch):
    assert db_initialisation.database_service(restarted=restarted) == restarted


@pytest.mark.unit
def test_setup_new_database(db_monkeypatch):
    db_test_conn = db_monkeypatch
    assert db_initialisation.setup_new_database(db_conn=db_test_conn) is None


@pytest.mark.unit
def test_make_db_admin_user(db_monkeypatch):
    db_test_conn = db_monkeypatch
    db_test_conn.execute_query(query="TRUNCATE TABLE cellar.owners")
    assert db_initialisation.make_db_admin_user(db_conn=db_test_conn) is None


@pytest.mark.unit
def test_check_for_cellar_db_exists(db_monkeypatch):
    db_test_conn = db_monkeypatch
    db_test_conn._cellar_exists = True
    db_test_conn._tables_exist = True
    assert db_initialisation.check_for_cellar_db(db_conn=db_test_conn)


@pytest.mark.unit
def test_check_for_cellar_db_not_exists(db_monkeypatch):
    db_test_conn = db_monkeypatch
    db_test_conn._cellar_exists = False
    assert not db_initialisation.check_for_cellar_db(db_conn=db_test_conn)


@pytest.mark.unit
def test_check_for_cellar_db_exists_incomplete(db_monkeypatch):
    db_test_conn = db_monkeypatch
    db_test_conn._cellar_exists = True
    db_test_conn._tables_exist = False
    assert not db_initialisation.check_for_cellar_db(db_conn=db_test_conn)


@pytest.mark.unit
def test_check_for_admin_user(db_monkeypatch):
    db_test_conn = db_monkeypatch
    assert db_initialisation.check_for_admin_user(db_conn=db_test_conn)


@pytest.mark.unit
def test_check_for_admin_user_not_exists(db_monkeypatch):
    db_test_conn = db_monkeypatch
    db_test_conn.execute_query(query="TRUNCATE TABLE cellar.owners")
    assert not db_initialisation.check_for_admin_user(db_conn=db_test_conn)
    db_initialisation.make_db_admin_user(db_conn=db_test_conn)
