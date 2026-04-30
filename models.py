# models.py
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Client(db.Model):
    """Модель клиента"""

    __tablename__ = "client"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    credit_card = db.Column(db.String(50), nullable=True)
    car_number = db.Column(db.String(10), nullable=True)

    # Связь с парковками
    parkings = db.relationship("ClientParking", backref="client", lazy=True)

    def __repr__(self):
        return f"<Client {self.name} {self.surname}>"


class Parking(db.Model):
    """Модель парковки"""

    __tablename__ = "parking"

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(100), nullable=False)
    opened = db.Column(db.Boolean, default=True)
    count_places = db.Column(db.Integer, nullable=False)
    count_available_places = db.Column(db.Integer, nullable=False)

    # Связь с клиентами
    clients = db.relationship("ClientParking", backref="parking", lazy=True)

    def __repr__(self):
        return f"<Parking {self.address}>"


class ClientParking(db.Model):
    """Лог въезда/выезда"""

    __tablename__ = "client_parking"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    parking_id = db.Column(db.Integer, db.ForeignKey("parking.id"), nullable=False)
    time_in = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    time_out = db.Column(db.DateTime, nullable=True)

    # Клиент не может быть дважды на одной парковке
    __table_args__ = (
        db.UniqueConstraint("client_id", "parking_id", name="unique_client_parking"),
    )

    def __repr__(self):
        return f"<ClientParking client={self.client_id} parking={self.parking_id}>"
