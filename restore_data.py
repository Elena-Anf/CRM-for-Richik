"""Restore test data: clients, pets, appointments"""
import asyncio, datetime
from app.core.database import async_session_factory
from app.models.client import Client
from app.models.pet import Pet
from app.models.appointment import Appointment
from app.models.master import Master
from app.models.service import Service
from sqlalchemy import select

NOW = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))

CLIENTS = [
    ("Ольга Смирнова", "+7 (916) 111-22-33"),
    ("Дмитрий Козлов", "+7 (916) 222-33-44"),
    ("Мария Иванова", "+7 (916) 333-44-55"),
    ("Сергей Новиков", "+7 (916) 444-55-66"),
    ("Анастасия Попова", "+7 (916) 555-66-77"),
    ("Иван Морозов", "+7 (916) 666-77-88"),
    ("Екатерина Волкова", "+7 (916) 777-88-99"),
]

PETS = [
    ("Рекс", "dog", "Золотистый ретривер"),
    ("Мурка", "cat", "Мейн-кун"),
    ("Бобик", "dog", "Корги"),
    ("Снежок", "dog", "Шпиц (померанский)"),
    ("Пушок", "cat", "Персидская"),
    ("Джек", "dog", "Джек-рассел-терьер"),
    ("Лола", "dog", "Мальтийская болонка"),
]

APPOINTMENTS = [
    # Past: completed
    {"days": -14, "hour": 10, "status": "completed", "client": 0, "pet": 0, "master": 1, "service": 1},
    {"days": -12, "hour": 11, "status": "completed", "client": 1, "pet": 1, "master": 2, "service": 2},
    {"days": -10, "hour": 14, "status": "completed", "client": 2, "pet": 2, "master": 1, "service": 3},
    {"days": -7, "hour": 9, "status": "completed", "client": 3, "pet": 3, "master": 2, "service": 4},
    {"days": -5, "hour": 16, "status": "completed", "client": 4, "pet": 4, "master": 3, "service": 5},
    {"days": -3, "hour": 10, "status": "completed", "client": 5, "pet": 5, "master": 1, "service": 6},
    {"days": -1, "hour": 12, "status": "completed", "client": 6, "pet": 6, "master": 3, "service": 1},
    # Future: pending/confirmed
    {"days": 1, "hour": 9, "status": "confirmed", "client": 0, "pet": 0, "master": 1, "service": 1},
    {"days": 1, "hour": 11, "status": "pending", "client": 2, "pet": 2, "master": 2, "service": 3},
    {"days": 2, "hour": 10, "status": "confirmed", "client": 3, "pet": 3, "master": 1, "service": 2},
    {"days": 2, "hour": 14, "status": "pending", "client": 5, "pet": 5, "master": 3, "service": 6},
    {"days": 3, "hour": 9, "status": "confirmed", "client": 1, "pet": 1, "master": 2, "service": 2},
    {"days": 3, "hour": 15, "status": "pending", "client": 4, "pet": 4, "master": 3, "service": 5},
    {"days": 5, "hour": 11, "status": "confirmed", "client": 6, "pet": 6, "master": 1, "service": 1},
    {"days": 7, "hour": 10, "status": "pending", "client": 0, "pet": 0, "master": 3, "service": 4},
]

async def restore():
    async with async_session_factory() as db:
        # Check existing data
        existing = (await db.execute(select(Client))).scalars().all()
        if existing:
            print(f"Data already exists ({len(existing)} clients), skipping.")
            return

        masters = {m.id: m for m in (await db.execute(select(Master))).scalars().all()}
        services = {s.id: s for s in (await db.execute(select(Service))).scalars().all()}

        # Create clients + pets
        for i, (name, phone) in enumerate(CLIENTS):
            c = Client(name=name, phone=phone)
            db.add(c)
            await db.flush()
            pn, ps, pb = PETS[i]
            p = Pet(client_id=c.id, name=pn, species=ps, breed=pb)
            db.add(p)
            await db.flush()

        await db.flush()

        # Reload clients with IDs
        all_clients = (await db.execute(select(Client))).scalars().all()
        all_pets = (await db.execute(select(Pet))).scalars().all()

        for a in APPOINTMENTS:
            client = all_clients[a["client"]]
            pet_list = [p for p in all_pets if p.client_id == client.id]
            pet = pet_list[0] if pet_list else all_pets[a["pet"]]
            master = masters.get(a["master"])
            service = services.get(a["service"])
            if not master or not service:
                continue

            start = NOW + datetime.timedelta(days=a["days"])
            start = start.replace(hour=a["hour"], minute=0, second=0, microsecond=0)
            end = start + datetime.timedelta(minutes=service.duration_minutes)
            earnings = round(service.price * master.commission_percent / 100, 2)

            appt = Appointment(
                client_id=client.id,
                pet_id=pet.id,
                master_id=master.id,
                service_id=service.id,
                start_time=start,
                end_time=end,
                status=a["status"],
                price=service.price,
                cost_price=service.cost_price,
                master_earnings=earnings,
                notes="",
            )
            db.add(appt)

        await db.commit()

        counts = {
            "clients": len(all_clients),
            "pets": len(all_pets),
            "appointments": len(APPOINTMENTS),
        }
        print("Restore complete!")
        print(f"  Clients: {counts['clients']}")
        print(f"  Pets: {counts['pets']}")
        print(f"  Appointments: {counts['appointments']}")

if __name__ == "__main__":
    asyncio.run(restore())
