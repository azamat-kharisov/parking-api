import pytest
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetEndpoints:
    """Тесты GET-методов с параметризацией"""

    @pytest.mark.parametrize("endpoint", [
        '/clients',
        '/parkings',
        '/'
    ])
    def test_get_endpoints_return_200(self, client, endpoint):
        """Проверяем, что все GET-эндпоинты возвращают код 200"""
        response = client.get(endpoint)
        assert response.status_code == 200


class TestCreateClient:
    """Тесты создания клиента"""

    def test_create_client_success(self, client):
        """Успешное создание клиента"""
        data = {
            'name': 'Анна',
            'surname': 'Сидорова',
            'credit_card': '9876-5432-1098-7654',
            'car_number': 'C789DE'
        }
        response = client.post('/clients', json=data)
        assert response.status_code == 201
        assert response.json['message'] == 'Клиент создан'
        assert 'id' in response.json


class TestCreateParking:
    """Тесты создания парковки"""

    def test_create_parking_success(self, client):
        """Успешное создание парковки"""
        data = {
            'address': 'ул. Пушкина, 10',
            'count_places': 20
        }
        response = client.post('/parkings', json=data)
        assert response.status_code == 201
        assert response.json['message'] == 'Парковка создана'
        assert 'id' in response.json


class TestEnterParking:
    """Тесты въезда на парковку (с маркером parking)"""

    @pytest.mark.parking
    def test_enter_parking_success(self, client, test_client, test_parking):
        """Успешный въезд на парковку"""
        initial_places = test_parking.count_available_places

        data = {
            'client_id': test_client.id,
            'parking_id': test_parking.id
        }
        response = client.post('/client_parkings', json=data)

        assert response.status_code == 201
        assert response.json['message'] == 'Въезд разрешен'
        assert response.json['available_places'] == initial_places - 1
        assert 'entry_id' in response.json

    @pytest.mark.parking
    def test_enter_closed_parking(self, client, test_client, test_parking_closed):
        """Въезд на закрытую парковку"""
        data = {
            'client_id': test_client.id,
            'parking_id': test_parking_closed.id
        }
        response = client.post('/client_parkings', json=data)

        assert response.status_code == 400
        assert 'Парковка закрыта' in response.json['error']

    @pytest.mark.parking
    def test_enter_full_parking(self, client, test_client, test_parking_full):
        """Въезд на полностью занятую парковку"""
        data = {
            'client_id': test_client.id,
            'parking_id': test_parking_full.id
        }
        response = client.post('/client_parkings', json=data)

        assert response.status_code == 400
        assert 'Свободных мест нет' in response.json['error']

    @pytest.mark.parking
    def test_enter_parking_twice(self, client, test_client, test_parking):
        """Повторный въезд на ту же парковку"""
        data = {
            'client_id': test_client.id,
            'parking_id': test_parking.id
        }
        # Первый въезд
        response1 = client.post('/client_parkings', json=data)
        assert response1.status_code == 201

        # Второй въезд
        response2 = client.post('/client_parkings', json=data)
        assert response2.status_code == 400
        assert 'уже на этой парковке' in response2.json['error']


class TestExitParking:
    """Тесты выезда с парковки (с маркером parking)"""

    @pytest.mark.parking
    def test_exit_parking_success(self, client, test_client, test_parking):
        """Успешный выезд с парковки"""
        # Сначала заезжаем
        enter_data = {
            'client_id': test_client.id,
            'parking_id': test_parking.id
        }
        initial_places = test_parking.count_available_places  # <-- ПЕРЕНОСИМ ДО въезда

        enter_response = client.post('/client_parkings', json=enter_data)
        assert enter_response.status_code == 201

        # Теперь выезжаем
        exit_data = {
            'client_id': test_client.id,
            'parking_id': test_parking.id
        }
        response = client.delete('/client_parkings', json=exit_data)

        assert response.status_code == 200
        assert response.json['message'] == 'Выезд разрешен'
        assert 'duration_hours' in response.json
        assert 'cost_rub' in response.json
        assert response.json['available_places'] == initial_places

    @pytest.mark.parking
    def test_exit_parking_without_card(self, client, test_client_no_card, test_parking):
        """Выезд клиента без кредитной карты"""
        # Заезжаем
        enter_data = {
            'client_id': test_client_no_card.id,
            'parking_id': test_parking.id
        }
        enter_response = client.post('/client_parkings', json=enter_data)
        assert enter_response.status_code == 201

        # Пытаемся выехать
        exit_data = {
            'client_id': test_client_no_card.id,
            'parking_id': test_parking.id
        }
        response = client.delete('/client_parkings', json=exit_data)

        assert response.status_code == 400
        assert 'Нет кредитной карты' in response.json['error']

    @pytest.mark.parking
    def test_exit_parking_no_active_entry(self, client, test_client, test_parking):
        """Выезд без активной записи о въезде"""
        data = {
            'client_id': test_client.id,
            'parking_id': test_parking.id
        }
        response = client.delete('/client_parkings', json=data)

        assert response.status_code == 404
        assert 'Нет активной записи' in response.json['error']

    @pytest.mark.parking
    def test_exit_parking_calculates_cost(self, client, test_client, test_parking):
        """Проверяем расчет стоимости парковки"""
        # Заезжаем
        enter_data = {
            'client_id': test_client.id,
            'parking_id': test_parking.id
        }
        enter_response = client.post('/client_parkings', json=enter_data)
        assert enter_response.status_code == 201
        entry_id = enter_response.json['entry_id']

        # Вручную изменяем время въезда в БД на 2.5 часа назад
        with client.application.app_context():
            from models import db, ClientParking
            entry = db.session.get(ClientParking, entry_id)
            entry.time_in = datetime.now(timezone.utc) - timedelta(hours=2, minutes=30)
            db.session.commit()

        # Выезжаем
        exit_data = {
            'client_id': test_client.id,
            'parking_id': test_parking.id
        }
        response = client.delete('/client_parkings', json=exit_data)

        assert response.status_code == 200
        # Допускаем небольшую погрешность
        assert 2.49 <= response.json['duration_hours'] <= 2.51
        expected_cost = round(response.json['duration_hours'] * 100, 2)
        assert response.json['cost_rub'] == expected_cost


class TestNegativeScenarios:
    """Негативные сценарии"""

    def test_enter_parking_missing_client_id(self, client, test_parking):
        """Въезд без указания client_id"""
        data = {'parking_id': test_parking.id}
        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'client_id и parking_id обязательны' in response.json['error']

    def test_enter_parking_missing_parking_id(self, client, test_client):
        """Въезд без указания parking_id"""
        data = {'client_id': test_client.id}
        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'client_id и parking_id обязательны' in response.json['error']

    def test_exit_parking_missing_client_id(self, client, test_parking):
        """Выезд без указания client_id"""
        data = {'parking_id': test_parking.id}
        response = client.delete('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'client_id и parking_id обязательны' in response.json['error']

    def test_exit_parking_missing_parking_id(self, client, test_client):
        """Выезд без указания parking_id"""
        data = {'client_id': test_client.id}
        response = client.delete('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'client_id и parking_id обязательны' in response.json['error']