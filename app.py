# app.py
from flask import Flask, request, jsonify
from models import db, Client, Parking, ClientParking
from datetime import datetime, timezone


def create_app():
    """Фабрика создания приложения"""
    app = Flask(__name__)

    # Конфигурация - БД создается в папке instance
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Инициализация БД
    db.init_app(app)

    # Создаем таблицы
    with app.app_context():
        db.create_all()

    # Регистрируем маршруты
    register_routes(app)

    return app


def register_routes(app):
    """Регистрация всех маршрутов API"""

    # ===== КЛИЕНТЫ =====

    @app.route('/clients', methods=['GET'])
    def get_clients():
        """Список всех клиентов"""
        clients = Client.query.all()
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'surname': c.surname,
            'credit_card': c.credit_card,
            'car_number': c.car_number
        } for c in clients]), 200

    @app.route('/clients/<int:client_id>', methods=['GET'])
    def get_client(client_id):
        """Информация о клиенте по ID"""
        client = db.session.get(Client, client_id)
        if not client:
            return jsonify({'error': 'Клиент не найден'}), 404
        return jsonify({
            'id': client.id,
            'name': client.name,
            'surname': client.surname,
            'credit_card': client.credit_card,
            'car_number': client.car_number
        }), 200

    @app.route('/clients', methods=['POST'])
    def create_client():
        """Создать нового клиента"""
        data = request.json

        if not data.get('name') or not data.get('surname'):
            return jsonify({'error': 'Имя и фамилия обязательны'}), 400

        client = Client(
            name=data['name'],
            surname=data['surname'],
            credit_card=data.get('credit_card'),
            car_number=data.get('car_number')
        )

        db.session.add(client)
        db.session.commit()
        return jsonify({'id': client.id, 'message': 'Клиент создан'}), 201

    # ===== ПАРКОВКИ =====

    @app.route('/parkings', methods=['GET'])
    def get_parkings():
        """Список всех парковок"""
        parkings = Parking.query.all()
        return jsonify([{
            'id': p.id,
            'address': p.address,
            'opened': p.opened,
            'count_places': p.count_places,
            'count_available_places': p.count_available_places
        } for p in parkings]), 200

    @app.route('/parkings', methods=['POST'])
    def create_parking():
        """Создать новую парковку"""
        data = request.json

        if not data.get('address') or not data.get('count_places'):
            return jsonify({'error': 'Адрес и количество мест обязательны'}), 400

        parking = Parking(
            address=data['address'],
            opened=data.get('opened', True),
            count_places=data['count_places'],
            count_available_places=data['count_places']
        )

        db.session.add(parking)
        db.session.commit()
        return jsonify({'id': parking.id, 'message': 'Парковка создана'}), 201

    # ===== ВЪЕЗД/ВЫЕЗД =====

    @app.route('/client_parkings', methods=['POST'])
    def enter_parking():
        """Заезд на парковку"""
        data = request.json
        client_id = data.get('client_id')
        parking_id = data.get('parking_id')

        if not client_id or not parking_id:
            return jsonify({'error': 'client_id и parking_id обязательны'}), 400

        client = db.session.get(Client, client_id)
        if not client:
            return jsonify({'error': 'Клиент не найден'}), 404

        parking = db.session.get(Parking, parking_id)
        if not parking:
            return jsonify({'error': 'Парковка не найдена'}), 404

        if not parking.opened:
            return jsonify({'error': 'Парковка закрыта'}), 400

        if parking.count_available_places <= 0:
            return jsonify({'error': 'Свободных мест нет'}), 400

        # Проверяем, не на парковке ли уже клиент
        active = ClientParking.query.filter_by(
            client_id=client_id, parking_id=parking_id, time_out=None
        ).first()
        if active:
            return jsonify({'error': 'Клиент уже на этой парковке'}), 400

        # Создаем запись о въезде
        entry = ClientParking(
            client_id=client_id,
            parking_id=parking_id,
            time_in=datetime.now(timezone.utc)
        )

        parking.count_available_places -= 1

        db.session.add(entry)
        db.session.commit()

        return jsonify({
            'message': 'Въезд разрешен',
            'entry_id': entry.id,
            'time_in': entry.time_in.isoformat(),
            'available_places': parking.count_available_places
        }), 201

    @app.route('/client_parkings', methods=['DELETE'])
    def exit_parking():
        """Выезд с парковки"""
        data = request.json
        client_id = data.get('client_id')
        parking_id = data.get('parking_id')

        if not client_id or not parking_id:
            return jsonify({'error': 'client_id и parking_id обязательны'}), 400

        client = db.session.get(Client, client_id)
        if not client:
            return jsonify({'error': 'Клиент не найден'}), 404

        if not client.credit_card:
            return jsonify({'error': 'Нет кредитной карты для оплаты'}), 400

        parking = db.session.get(Parking, parking_id)
        if not parking:
            return jsonify({'error': 'Парковка не найдена'}), 404

        # Ищем активную запись о въезде
        entry = ClientParking.query.filter_by(
            client_id=client_id, parking_id=parking_id, time_out=None
        ).first()

        if not entry:
            return jsonify({'error': 'Нет активной записи о въезде'}), 404

        # Регистрируем выезд
        entry.time_out = datetime.now(timezone.utc)
        parking.count_available_places += 1

        # Приводим оба времени к timezone-aware (на всякий случай)
        time_in = entry.time_in
        time_out = entry.time_out
        if time_in.tzinfo is None:
            time_in = time_in.replace(tzinfo=timezone.utc)
        if time_out.tzinfo is None:
            time_out = time_out.replace(tzinfo=timezone.utc)

        # Рассчитываем стоимость (100 руб/час)
        duration_hours = (time_out - time_in).total_seconds() / 3600
        cost = round(duration_hours * 100, 2)

        db.session.commit()

        return jsonify({
            'message': 'Выезд разрешен',
            'entry_id': entry.id,
            'time_in': entry.time_in.isoformat(),
            'time_out': entry.time_out.isoformat(),
            'duration_hours': round(duration_hours, 2),
            'cost_rub': cost,
            'available_places': parking.count_available_places
        }), 200

    @app.route('/')
    def index():
        """Главная страница"""
        return jsonify({
            'status': 'ok',
            'message': 'Parking API работает',
            'endpoints': {
                'GET /clients': 'Список клиентов',
                'GET /clients/<id>': 'Клиент по ID',
                'POST /clients': 'Создать клиента',
                'GET /parkings': 'Список парковок',
                'POST /parkings': 'Создать парковку',
                'POST /client_parkings': 'Въезд (body: client_id, parking_id)',
                'DELETE /client_parkings': 'Выезд (body: client_id, parking_id)'
            }
        }), 200


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)