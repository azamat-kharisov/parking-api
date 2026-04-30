# tests/test_api.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import create_app
from models import db, Client, Parking


@pytest.fixture
def app():
    """Фикстура приложения для тестов API"""
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
def sample_client(app):
    """Создание тестового клиента в БД - возвращаем ID, а не объект"""
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
def sample_parking(app):
    """Создание тестовой парковки в БД - возвращаем ID, а не объект"""
    with app.app_context():
        parking = Parking(
            address="ул. Ленина, 1",
            opened=True,
            count_places=10,
            count_available_places=10
        )
        db.session.add(parking)
        db.session.commit()
        return parking.id


class TestClientsAPI:
    """Тесты API для клиентов"""

    def test_get_clients_empty(self, client):
        """Тест получения списка клиентов (пустой)"""
        response = client.get('/clients')
        assert response.status_code == 200
        assert response.json == []

    def test_create_client_success(self, client):
        """Тест успешного создания клиента"""
        data = {
            'name': 'Тест',
            'surname': 'Тестовый',
            'credit_card': '123456789',
            'car_number': 'A777AA'
        }
        response = client.post('/clients', json=data)
        assert response.status_code == 201
        assert response.json['message'] == 'Клиент создан'
        assert 'id' in response.json

    def test_create_client_missing_fields(self, client):
        """Тест создания клиента без обязательных полей"""
        data = {'name': 'Тест'}
        response = client.post('/clients', json=data)
        assert response.status_code == 400
        assert 'error' in response.json

    def test_get_client_by_id(self, client, sample_client):
        """Тест получения клиента по ID"""
        response = client.get(f'/clients/{sample_client}')
        assert response.status_code == 200
        assert response.json['name'] == 'Иван'
        assert response.json['surname'] == 'Петров'

    def test_get_client_not_found(self, client):
        """Тест получения несуществующего клиента"""
        response = client.get('/clients/999')
        assert response.status_code == 404
        assert 'error' in response.json


class TestParkingsAPI:
    """Тесты API для парковок"""

    def test_create_parking_success(self, client):
        """Тест успешного создания парковки"""
        data = {
            'address': 'Новая парковка',
            'count_places': 50
        }
        response = client.post('/parkings', json=data)
        assert response.status_code == 201
        assert response.json['message'] == 'Парковка создана'

    def test_create_parking_without_address(self, client):
        """Тест создания парковки без адреса"""
        data = {'count_places': 50}
        response = client.post('/parkings', json=data)
        assert response.status_code == 400

    def test_get_parkings(self, client, sample_parking):
        """Тест получения списка парковок"""
        response = client.get('/parkings')
        assert response.status_code == 200
        assert len(response.json) == 1
        assert response.json[0]['address'] == 'ул. Ленина, 1'


class TestParkingOperationsAPI:
    """Тесты операций въезда/выезда"""

    def test_enter_parking_success(self, client, sample_client, sample_parking):
        """Тест успешного въезда на парковку"""
        data = {
            'client_id': sample_client,
            'parking_id': sample_parking
        }
        response = client.post('/client_parkings', json=data)
        assert response.status_code == 201
        assert response.json['message'] == 'Въезд разрешен'
        assert 'entry_id' in response.json
        assert response.json['available_places'] == 9

    def test_enter_parking_no_free_places(self, client, sample_client):
        """Тест въезда на полностью занятую парковку"""
        with client.application.app_context():
            full_parking = Parking(
                address="Полная парковка",
                count_places=1,
                count_available_places=0
            )
            db.session.add(full_parking)
            db.session.commit()
            parking_id = full_parking.id

        data = {
            'client_id': sample_client,
            'parking_id': parking_id
        }
        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'Свободных мест нет' in response.json['error']

    def test_enter_parking_closed(self, client, sample_client):
        """Тест въезда на закрытую парковку"""
        with client.application.app_context():
            closed_parking = Parking(
                address="Закрытая парковка",
                opened=False,
                count_places=10,
                count_available_places=10
            )
            db.session.add(closed_parking)
            db.session.commit()
            parking_id = closed_parking.id

        data = {
            'client_id': sample_client,
            'parking_id': parking_id
        }
        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'Парковка закрыта' in response.json['error']

    def test_enter_parking_already_inside(self, client, sample_client, sample_parking):
        """Тест повторного въезда на ту же парковку"""
        data = {
            'client_id': sample_client,
            'parking_id': sample_parking
        }
        client.post('/client_parkings', json=data)
        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'уже на этой парковке' in response.json['error']

    def test_exit_parking_success(self, client, sample_client, sample_parking):
        """Тест успешного выезда с парковки"""
        enter_data = {
            'client_id': sample_client,
            'parking_id': sample_parking
        }
        client.post('/client_parkings', json=enter_data)

        exit_data = {
            'client_id': sample_client,
            'parking_id': sample_parking
        }
        response = client.delete('/client_parkings', json=exit_data)
        assert response.status_code == 200
        assert response.json['message'] == 'Выезд разрешен'
        assert 'duration_hours' in response.json
        assert 'cost_rub' in response.json
        assert response.json['available_places'] == 10

    def test_exit_parking_no_card(self, client, sample_parking):
        """Тест выезда клиента без кредитной карты"""
        with client.application.app_context():
            client_no_card = Client(
                name="Без",
                surname="Карты",
                credit_card=None,
                car_number="B000BB"
            )
            db.session.add(client_no_card)
            db.session.commit()
            client_id = client_no_card.id

        enter_data = {
            'client_id': client_id,
            'parking_id': sample_parking
        }
        client.post('/client_parkings', json=enter_data)

        exit_data = {
            'client_id': client_id,
            'parking_id': sample_parking
        }
        response = client.delete('/client_parkings', json=exit_data)
        assert response.status_code == 400
        assert 'Нет кредитной карты' in response.json['error']

    def test_exit_parking_no_active_entry(self, client, sample_client, sample_parking):
        """Тест выезда без активного въезда"""
        data = {
            'client_id': sample_client,
            'parking_id': sample_parking
        }
        response = client.delete('/client_parkings', json=data)
        assert response.status_code == 404
        assert 'Нет активной записи' in response.json['error']
