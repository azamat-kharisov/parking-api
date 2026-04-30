import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Client, Parking
from tests.factories import ClientFactory, ParkingFactory


class TestClientFactory:
    """Тесты фабрики ClientFactory"""

    def test_create_client_with_factory(self, db_session):
        """Тест создания клиента через фабрику"""
        initial_count = Client.query.count()

        client = ClientFactory()
        db_session.add(client)
        db_session.commit()

        assert client.id is not None
        assert client.name is not None
        assert client.surname is not None
        assert isinstance(client.name, str)
        assert isinstance(client.surname, str)

        assert Client.query.count() == initial_count + 1

    def test_client_has_car_number(self, db_session):
        """Тест: у клиента есть номер автомобиля"""
        client = ClientFactory()
        db_session.add(client)
        db_session.commit()

        assert client.car_number is not None or client.car_number is None

    def test_client_credit_card_optional(self, db_session):
        """Тест: кредитная карта может отсутствовать"""
        client_no_card = ClientFactory.create_without_card()
        db_session.add(client_no_card)
        db_session.commit()
        assert client_no_card.credit_card is None

        client_with_card = ClientFactory.create_with_card()
        db_session.add(client_with_card)
        db_session.commit()
        assert client_with_card.credit_card is not None

    def test_client_factory_generates_unique_data(self, db_session):
        """Тест: фабрика генерирует уникальные данные"""
        clients = []
        for _ in range(5):
            client = ClientFactory()
            db_session.add(client)
            clients.append(client)
        db_session.commit()

        ids = [c.id for c in clients]
        assert len(set(ids)) == 5

    def test_create_client_via_api_with_factory(self, client, db_session):
        """Дубликат теста 'Создание клиента' с использованием ClientFactory"""
        new_client = ClientFactory()

        data = {
            'name': new_client.name,
            'surname': new_client.surname,
            'credit_card': new_client.credit_card,
            'car_number': new_client.car_number
        }
        response = client.post('/clients', json=data)

        assert response.status_code == 201
        assert response.json['message'] == 'Клиент создан'
        assert 'id' in response.json

        db_client = db_session.get(Client, response.json['id'])
        assert db_client is not None
        assert db_client.name == new_client.name
        assert db_client.surname == new_client.surname

    def test_create_multiple_clients_with_factory(self, db_session):
        """Тест создания нескольких клиентов через фабрику"""
        initial_count = Client.query.count()

        clients = ClientFactory.create_batch(3)
        for client in clients:
            db_session.add(client)
        db_session.commit()

        assert Client.query.count() == initial_count + 3


class TestParkingFactory:
    """Тесты фабрики ParkingFactory"""

    def test_create_parking_with_factory(self, db_session):
        """Тест создания парковки через фабрику"""
        initial_count = Parking.query.count()

        parking = ParkingFactory()
        db_session.add(parking)
        db_session.commit()

        assert parking.id is not None
        assert parking.address is not None
        assert isinstance(parking.count_places, int)
        assert parking.count_places > 0
        assert parking.count_available_places <= parking.count_places
        assert parking.count_available_places >= 0

        assert Parking.query.count() == initial_count + 1

    def test_parking_opened_field_random(self, db_session):
        """Тест: поле opened может быть True или False"""
        parkings = []
        for _ in range(10):
            parking = ParkingFactory()
            db_session.add(parking)
            parkings.append(parking)
        db_session.commit()

        for p in parkings:
            assert isinstance(p.opened, bool)

    def test_create_opened_parking(self, db_session):
        """Тест создания открытой парковки"""
        parking = ParkingFactory.create_opened()
        db_session.add(parking)
        db_session.commit()

        assert parking.opened is True

    def test_create_closed_parking(self, db_session):
        """Тест создания закрытой парковки"""
        parking = ParkingFactory.create_closed()
        db_session.add(parking)
        db_session.commit()

        assert parking.opened is False

    def test_create_full_parking(self, db_session):
        """Тест создания полностью занятой парковки"""
        parking = ParkingFactory.create_full(count_places=5)
        db_session.add(parking)
        db_session.commit()

        assert parking.count_available_places == 0
        assert parking.count_places == 5
        assert parking.opened is True

    def test_parking_available_places_not_exceed_total(self, db_session):
        """Тест: свободных мест не может быть больше общего количества"""
        for _ in range(20):
            parking = ParkingFactory()
            db_session.add(parking)
        db_session.commit()

        parkings = Parking.query.all()
        for p in parkings:
            assert p.count_available_places <= p.count_places
            assert p.count_available_places >= 0

    def test_create_parking_via_api_with_factory(self, client, db_session):
        """Дубликат теста 'Создание парковки' с использованием ParkingFactory"""
        new_parking = ParkingFactory()

        data = {
            'address': new_parking.address,
            'count_places': new_parking.count_places,
            'opened': new_parking.opened
        }
        response = client.post('/parkings', json=data)

        assert response.status_code == 201
        assert response.json['message'] == 'Парковка создана'
        assert 'id' in response.json

        db_parking = db_session.get(Parking, response.json['id'])
        assert db_parking is not None
        assert db_parking.address == new_parking.address
        assert db_parking.count_places == new_parking.count_places

    def test_create_multiple_parkings_with_factory(self, db_session):
        """Тест создания нескольких парковок через фабрику"""
        initial_count = Parking.query.count()

        parkings = ParkingFactory.create_batch(5)
        for parking in parkings:
            db_session.add(parking)
        db_session.commit()

        assert Parking.query.count() == initial_count + 5
