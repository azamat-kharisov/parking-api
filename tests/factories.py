# tests/factories.py
import random

import factory
from faker import Faker

from models import Client, Parking

fake = Faker()


class ClientFactory(factory.Factory):
    """Фабрика для создания тестовых клиентов"""

    class Meta:
        model = Client

    # Генерация имени (First name)
    name = factory.Faker("first_name")

    # Генерация фамилии (Last name)
    surname = factory.Faker("last_name")

    # Кредитная карта: либо None, либо реальный номер карты
    @factory.lazy_attribute
    def credit_card(self):
        # 70% клиентов имеют карту, 30% не имеют
        if random.random() < 0.7:
            return fake.credit_card_number()

        return None

    # Генерация номера автомобиля (например: A123BC или 123ABC)
    @factory.lazy_attribute
    def car_number(self):
        # Варианты генерации номеров
        patterns = [
            fake.license_plate(),  # Стандартный номер
            f"{random.choice('ABCEHKMOPTXY')}{random.randint(100, 999)}{random.choice('ABCEHKMOPTXY')}{random.choice('ABCEHKMOPTXY')}",
            # A123BC
            f"{random.randint(100, 999)}{random.choice('ABCEHKMOPTXY')}{random.choice('ABCEHKMOPTXY')}",  # 123AB
        ]
        return random.choice(patterns)

    # Можно добавить метод для создания клиента с картой
    @classmethod
    def create_with_card(cls, **kwargs):
        kwargs["credit_card"] = fake.credit_card_number()
        return cls.create(**kwargs)

    # Метод для создания клиента без карты
    @classmethod
    def create_without_card(cls, **kwargs):
        kwargs["credit_card"] = None
        return cls.create(**kwargs)


class ParkingFactory(factory.Factory):
    """Фабрика для создания тестовых парковок"""

    class Meta:
        model = Parking

    # Генерация адреса
    address = factory.Faker("address")

    # Парковка может быть открыта или закрыта (случайно)
    opened = factory.LazyFunction(lambda: random.choice([True, False]))

    # Количество мест (от 5 до 100)
    count_places = factory.LazyFunction(lambda: random.randint(5, 100))

    # Количество свободных мест (LazyAttribute - вычисляется на основе count_places)
    @factory.lazy_attribute
    def count_available_places(self):
        # Свободных мест может быть от 0 до count_places
        return random.randint(0, self.count_places)

    # Метод для создания открытой парковки
    @classmethod
    def create_opened(cls, **kwargs):
        kwargs["opened"] = True
        return cls.create(**kwargs)

    # Метод для создания закрытой парковки
    @classmethod
    def create_closed(cls, **kwargs):
        kwargs["opened"] = False
        return cls.create(**kwargs)

    # Метод для создания полностью заполненной парковки
    @classmethod
    def create_full(cls, count_places=None, **kwargs):
        if count_places:
            kwargs["count_places"] = count_places
        else:
            kwargs["count_places"] = random.randint(5, 50)
        kwargs["count_available_places"] = 0
        kwargs["opened"] = True
        return cls.create(**kwargs)
