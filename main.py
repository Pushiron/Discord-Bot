import asyncio
import sqlite3
import discord
from discord.ext import commands

# Установка соединения с базой данных
connection = sqlite3.connect('master_rooms.db')
cursor = connection.cursor()

intents = intents = discord.Intents.all()
intents.voice_states = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)


# Команды
@bot.command()
async def create_master_room(ctx, *, args):
    # Разделение аргументов по запятой
    arguments = [arg.strip() for arg in args.split(',')]

    # Проверка наличия всех аргументов
    if len(arguments) != 4:
        await ctx.send("Неверное количество аргументов.")
        return

    try:
        category_id = int(arguments[0])
        master_room_name = arguments[1]
        default_name = arguments[2]
        u_ammount = int(arguments[3])
    except ValueError:
        await ctx.send("Неверный тип данных для аргументов.")
        return

    # Получение объекта категории по ID
    category = bot.get_channel(category_id)

    # Проверка, что категория существует
    if category is None or not isinstance(category, discord.CategoryChannel):
        await ctx.send("Указанная категория не найдена.")
        return

    # Создание мастер комнаты в указанной категории
    master_channel = await category.create_voice_channel(name=f'➕ {master_room_name}') 

    # Сохранение значений в базу данных
    cursor.execute("INSERT INTO master_rooms (masterroom_id, default_name, u_ammount) VALUES (?, ?, ?)", (master_channel.id, default_name, u_ammount))
    connection.commit()

    await ctx.send(f"Мастер комната '{master_room_name}' успешно создана.")


# Ивенты
@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')

    # Создание таблицы master_rooms, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS master_rooms (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        masterroom_id INTEGER,
                        default_name TEXT,
                        u_ammount INTEGER
                    )''')

    # Создание таблицы temp_channels, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS temp_channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        temp_id INTEGER
                    )''')

    connection.commit()


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None:
        masterroom_id = cursor.execute("SELECT masterroom_id FROM master_rooms WHERE masterroom_id=?", (after.channel.id,)).fetchone()
        if masterroom_id is not None:
            default_name = cursor.execute("SELECT default_name FROM master_rooms WHERE masterroom_id=?", (masterroom_id[0],)).fetchone()
            if default_name is not None:
                u_ammount = cursor.execute("SELECT u_ammount FROM master_rooms WHERE masterroom_id=?", (masterroom_id[0],)).fetchone()
                limit = u_ammount[0]
                category = after.channel.category
                if category is not None:
                    if limit == 0:
                        new_channel = await category.create_voice_channel(name=default_name[0])
                        await member.move_to(new_channel)
                        cursor.execute("INSERT INTO temp_channels (temp_id) VALUES (?)", (new_channel.id,))
                        connection.commit()
                    else:
                        new_channel = await category.create_voice_channel(name=default_name[0], user_limit=limit)
                        await member.move_to(new_channel)
                        cursor.execute("INSERT INTO temp_channels (temp_id) VALUES (?)", (new_channel.id,))
                        connection.commit()


    if before.channel is not None and before.channel.id in [temp[0] for temp in cursor.execute(
            "SELECT temp_id FROM temp_channels").fetchall()]:
        temp_channel = bot.get_channel(before.channel.id)
        if temp_channel is not None and len(temp_channel.members) == 0:
            await asyncio.sleep(1)  # Задержка на 1 секунду
            await temp_channel.delete()
            cursor.execute("DELETE FROM temp_channels WHERE temp_id=?", (temp_channel.id,))
            connection.commit()


@bot.event
async def on_disconnect():
    connection.close()


bot.run('MTEyMTM3OTQwMzkyMjkzNTg3OA.G4WG-k.Fj9u7puH4NgeTDaDvEUaKcvVSt1_SBDG6w9Bew')
