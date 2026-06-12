"""Seed script — creates initial data for first run.
Run: python seed.py
"""
import asyncio
from app.core.database import async_session_factory, init_db
from app.core.security import hash_password
from app.models.user import User
from app.models.master import Master
from app.models.service import Service
from app.models.breed import Breed


async def seed():
    await init_db()

    async with async_session_factory() as db:
        existing = await db.get(Master, 1)
        if existing:
            print("Database already has data, skipping seed.")
            return

        admin = User(
            username="admin",
            email="admin@grooming.ru",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        db.add(admin)

        master = Master(
            name="Анна Петрова",
            phone="+7 (999) 123-45-67",
            bio="Мастер-грумер с 5-летним опытом",
            color="#4F46E5",
            commission_percent=40.0,
        )
        db.add(master)

        master2 = Master(
            name="Елена Соколова",
            phone="+7 (999) 765-43-21",
            bio="Специалист по кошкам и мелким породам",
            color="#7C3AED",
            commission_percent=45.0,
        )
        db.add(master2)

        services = [
            Service(name="Комплекс — стрижка", duration_minutes=90, price=2500, cost_price=300, category="стрижка"),
            Service(name="Комплекс — тримминг", duration_minutes=120, price=3000, cost_price=350, category="тримминг"),
            Service(name="Моем + сушка", duration_minutes=60, price=1500, cost_price=200, category="гигиена"),
            Service(name="Когти + уши + лапы", duration_minutes=30, price=800, cost_price=50, category="гигиена"),
            Service(name="Стрижка когтей", duration_minutes=15, price=400, cost_price=20, category="гигиена"),
            Service(name="Экспресс-линька", duration_minutes=90, price=3500, cost_price=500, category="специальный"),
        ]
        for s in services:
            db.add(s)

        breeds = [
            Breed(name="Йоркширский терьер", species="dog", sort_order=1),
            Breed(name="Чихуахуа", species="dog", sort_order=2),
            Breed(name="Той-пудель", species="dog", sort_order=3),
            Breed(name="Мальтийская болонка", species="dog", sort_order=4),
            Breed(name="Шпиц (померанский)", species="dog", sort_order=5),
            Breed(name="Ши-тцу", species="dog", sort_order=6),
            Breed(name="Французский бульдог", species="dog", sort_order=7),
            Breed(name="Мопс", species="dog", sort_order=8),
            Breed(name="Лабрадор", species="dog", sort_order=9),
            Breed(name="Золотистый ретривер", species="dog", sort_order=10),
            Breed(name="Немецкая овчарка", species="dog", sort_order=11),
            Breed(name="Хаски", species="dog", sort_order=12),
            Breed(name="Корги", species="dog", sort_order=13),
            Breed(name="Шнауцер", species="dog", sort_order=14),
            Breed(name="Такса", species="dog", sort_order=15),
            Breed(name="Бишон фризе", species="dog", sort_order=16),
            Breed(name="Китайская хохлатая", species="dog", sort_order=17),
            Breed(name="Джек-рассел-терьер", species="dog", sort_order=18),
            Breed(name="Бигль", species="dog", sort_order=19),
            Breed(name="Акита-ину", species="dog", sort_order=20),
            Breed(name="Сиамская", species="cat", sort_order=50),
            Breed(name="Персидская", species="cat", sort_order=51),
            Breed(name="Мейн-кун", species="cat", sort_order=52),
            Breed(name="Британская короткошёрстная", species="cat", sort_order=53),
            Breed(name="Шотландская вислоухая", species="cat", sort_order=54),
            Breed(name="Сфинкс", species="cat", sort_order=55),
            Breed(name="Бенгальская", species="cat", sort_order=56),
            Breed(name="Кролик", species="other", sort_order=100),
            Breed(name="Морская свинка", species="other", sort_order=101),
            Breed(name="Хорёк", species="other", sort_order=102),
        ]
        for b in breeds:
            db.add(b)

        await db.commit()
        print("Seed complete!")
        print("  Admin login: admin / admin123")
        print(f"  Masters: {len([master, master2])}")
        print(f"  Services: {len(services)}")
        print(f"  Breeds: {len(breeds)}")


if __name__ == "__main__":
    asyncio.run(seed())
