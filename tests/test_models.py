# tests/test_models.py
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import create_app
from models import db, Client, Parking, ClientParking


@pytest.fixture
def app():
    """Фикстура приложения для тестов"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Фикстура тестового клиента - возвращаем ID вместо объекта"""
    with app.app_context():
        client = Client(
            name="Иван",
            surname="Петров",
            credit_card="1234-5678-9012-3456",
            car_number="A123BC"
        )
        db.session.add(client)
        db.session.commit()
        return client.id


@pytest.fixture
def parking(app):
    """Фикстура тестовой парковки - возвращаем ID вместо объекта"""
    with app.app_context():
        parking = Parking(
            address="ул. Ленина, 1",
            opened=True,
            count_places=50,
            count_available_places=50
        )
        db.session.add(parking)
        db.session.commit()
        return parking.id


class TestClientModel:
    """Тесты модели Client"""

    def test_create_client(self, app):
        """Тест создания клиента"""
        with app.app_context():
            client = Client(
                name="Тест",
                surname="Тестовый",
                credit_card="123456789",
                car_number="A777AA"
            )
            db.session.add(client)
            db.session.commit()

            assert client.id is not None
            assert client.name == "Тест"
            assert client.surname == "Тестовый"
            assert client.credit_card == "123456789"

    def test_client_repr(self, app, client):
        """Тест строкового представления клиента"""
        with app.app_context():
            client_obj = db.session.get(Client, client)
            assert repr(client_obj) == f"<Client {client_obj.name} {client_obj.surname}>"

    def test_get_client_from_db(self, app, client):
        """Тест получения клиента из БД"""
        with app.app_context():
            fetched = db.session.get(Client, client)
            assert fetched is not None
            assert fetched.name == "Иван"
            assert fetched.car_number == "A123BC"


class TestParkingModel:
    """Тесты модели Parking"""

    def test_create_parking(self, app):
        """Тест создания парковки"""
        with app.app_context():
            parking = Parking(
                address="Тестовая улица, 10",
                opened=True,
                count_places=100,
                count_available_places=100
            )
            db.session.add(parking)
            db.session.commit()

            assert parking.id is not None
            assert parking.address == "Тестовая улица, 10"
            assert parking.opened is True
            assert parking.count_places == 100

    def test_parking_repr(self, app, parking):
        """Тест строкового представления парковки"""
        with app.app_context():
            parking_obj = db.session.get(Parking, parking)
            assert repr(parking_obj) == f"<Parking {parking_obj.address}>"

    def test_parking_default_opened(self, app):
        """Тест значения по умолчанию для opened"""
        with app.app_context():
            parking = Parking(
                address="Новая парковка",
                count_places=20,
                count_available_places=20
            )
            db.session.add(parking)
            db.session.commit()

            assert parking.opened is True


class TestClientParkingModel:
    """Тесты модели ClientParking"""

    def test_create_entry(self, app, client, parking):
        """Тест создания записи о въезде"""
        with app.app_context():
            entry = ClientParking(
                client_id=client,
                parking_id=parking,
                time_in=datetime.now(timezone.utc)
            )
            db.session.add(entry)
            db.session.commit()

            assert entry.id is not None
            assert entry.time_out is None
            assert entry.client_id == client
            assert entry.parking_id == parking

    def test_unique_constraint(self, app, client, parking):
        """Тест уникального ограничения"""
        with app.app_context():
            entry1 = ClientParking(client_id=client, parking_id=parking)
            db.session.add(entry1)
            db.session.commit()

            entry2 = ClientParking(client_id=client, parking_id=parking)
            db.session.add(entry2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_time_out(self, app, client, parking):
        """Тест записи времени выезда"""
        with app.app_context():
            entry = ClientParking(
                client_id=client,
                parking_id=parking,
                time_in=datetime.now(timezone.utc) - timedelta(hours=2)
            )
            db.session.add(entry)
            db.session.commit()

            entry.time_out = datetime.now(timezone.utc)
            db.session.commit()

            assert entry.time_out is not None
            assert entry.time_out > entry.time_in

    def test_default_time_in(self, app, client, parking):
        """Тест автоматической установки времени въезда"""
        with app.app_context():
            entry = ClientParking(
                client_id=client,
                parking_id=parking
            )
            db.session.add(entry)
            db.session.commit()

            assert entry.time_in is not None
            assert isinstance(entry.time_in, datetime)


class TestRelationships:
    """Тесты связей между моделями"""

    def test_client_parking_relationship(self, app, client, parking):
        """Тест связи клиент-парковка"""
        with app.app_context():
            entry = ClientParking(client_id=client, parking_id=parking)
            db.session.add(entry)
            db.session.commit()

            client_obj = db.session.get(Client, client)
            parking_obj = db.session.get(Parking, parking)

            assert len(client_obj.parkings) == 1
            assert client_obj.parkings[0].parking_id == parking

            assert len(parking_obj.clients) == 1
            assert parking_obj.clients[0].client_id == client

    def test_multiple_entries_for_client(self, app, client):
        """Тест множественных записей для одного клиента на разных парковках"""
        with app.app_context():
            parking1 = Parking(
                address="Парковка 1",
                count_places=10,
                count_available_places=10
            )
            parking2 = Parking(
                address="Парковка 2",
                count_places=20,
                count_available_places=20
            )
            db.session.add_all([parking1, parking2])
            db.session.commit()

            entry1 = ClientParking(client_id=client, parking_id=parking1.id)
            entry2 = ClientParking(client_id=client, parking_id=parking2.id)
            db.session.add_all([entry1, entry2])
            db.session.commit()

            client_obj = db.session.get(Client, client)

            assert len(client_obj.parkings) == 2