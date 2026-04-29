import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Client, Parking, ClientParking
from tests.factories import ClientFactory, ParkingFactory


@pytest.fixture
def app():
    """Фикстура приложения"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Тестовый клиент Flask"""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Фикстура сессии БД"""
    with app.app_context():
        yield db.session


@pytest.fixture
def test_client(db_session):
    """Создает тестового клиента через фабрику"""
    client = ClientFactory()
    db_session.add(client)
    db_session.commit()
    return client


@pytest.fixture
def test_client_no_card(db_session):
    """Создает клиента без кредитной карты"""
    client = ClientFactory.create_without_card()
    db_session.add(client)
    db_session.commit()
    return client


@pytest.fixture
def test_parking(db_session):
    """Создает ОТКРЫТУЮ парковку со свободными местами"""
    parking = ParkingFactory.create_opened()
    # Убеждаемся, что есть свободные места
    if parking.count_available_places == 0:
        parking.count_available_places = parking.count_places
    db_session.add(parking)
    db_session.commit()
    return parking


@pytest.fixture
def test_parking_closed(db_session):
    """Создает закрытую парковку"""
    parking = ParkingFactory.create_closed()
    db_session.add(parking)
    db_session.commit()
    return parking


@pytest.fixture
def test_parking_full(db_session):
    """Создает полностью занятую парковку"""
    parking = ParkingFactory.create_full(count_places=5)
    parking.opened = True
    db_session.add(parking)
    db_session.commit()
    return parking


@pytest.fixture
def test_parking_entry(db_session, test_client, test_parking):
    """Создает запись о въезде"""
    entry = ClientParking(
        client_id=test_client.id,
        parking_id=test_parking.id,
        time_in=datetime.now(timezone.utc)
    )
    db_session.add(entry)
    test_parking.count_available_places -= 1
    db_session.commit()
    return entry