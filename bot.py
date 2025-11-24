import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN, ADMIN_TELEGRAM_IDS
from database import init_db, SessionLocal, User, Sale
from sqlalchemy import select

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Это бот учёта продаж.\nИспользуй /register чтобы начать.")

@dp.message(Command("register"))
async def register(message: types.Message):
    async with SessionLocal() as session:
        q = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = q.scalar_one_or_none()
        if user:
            return await message.answer("Вы уже зарегистрированы.")
        role = "admin" if message.from_user.id in ADMIN_TELEGRAM_IDS else "seller"
        new_user = User(telegram_id=message.from_user.id, name=message.from_user.full_name, role=role)
        session.add(new_user)
        await session.commit()
    await message.answer(f"Регистрация успешна! Ваша роль: {role}")

@dp.message(Command("add"))
async def add_sale(message: types.Message):
    await message.answer("Введите продажу в формате:\nТовар, цена, себестоимость")

@dp.message()
async def handle_msg(message: types.Message):
    text = message.text.strip()
    if "," in text:
        try:
            product, sale, cost = [x.strip() for x in text.split(",")]
            sale = float(sale); cost = float(cost)
            profit = sale - cost
        except:
            return await message.answer("Ошибка формата. Пример: Ручка, 1200, 700")
        async with SessionLocal() as session:
            q = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = q.scalar_one_or_none()
            if not user:
                return await message.answer("Сначала выполните /register")
            new_sale = Sale(user_id=user.id, product=product, sale_price=sale, cost_price=cost, profit=profit)
            session.add(new_sale); await session.commit()
        return await message.answer(f"Продажа добавлена.\nПрибыль: {profit}")
    return await message.answer("Команда не распознана.")

@dp.message(Command("stats"))
async def stats(message: types.Message):
    async with SessionLocal() as session:
        q = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = q.scalar_one_or_none()
        if not user:
            return await message.answer("Сначала выполните /register")
        if user.role == "admin":
            raw = await session.execute("SELECT SUM(sale_price), SUM(cost_price), SUM(profit) FROM sales")
        else:
            raw = await session.execute(
                f"SELECT SUM(sale_price), SUM(cost_price), SUM(profit) FROM sales WHERE user_id = {user.id}"
            )
        data = raw.fetchone()
        revenue = data[0] or 0; cost = data[1] or 0; profit = data[2] or 0
        await message.answer(f"📊 Статистика:\nВыручка: {revenue}\nСебестоимость: {cost}\nПрибыль: {profit}")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
