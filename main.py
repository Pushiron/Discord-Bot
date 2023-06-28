import asyncio
import sqlite3
from config import TOKEN
import disnake
from disnake.ext import commands
from embeds import add_to_embed

# Установка соединения с базой данных
connection = sqlite3.connect('master_rooms.db')
cursor = connection.cursor()

intents = disnake.Intents.all()
intents.voice_states = True
intents.messages = True

bot = commands.Bot(command_prefix='!', help_command=None, intents=intents)

# Команды
@bot.slash_command(description="Создание мастер комнаты")
@commands.has_permissions(manage_channels=True)
async def erm_create(
        ctx,
        category_id=commands.Param(description="ID категории"),
        mr_name=commands.Param(default="Мастер комната", description='Имя Мастер комнаты'),
        room_name=commands.Param(default="Временная комната", description='Имя временных комнат'),
        limit=commands.Param(default=0, description='Лимит пользователей')
    ):

    # Получение объекта категории по ID
    category = disnake.utils.get(ctx.guild.categories, id=int(category_id))

    # Проверка, что категория существует
    if category is None or not isinstance(category, disnake.CategoryChannel):
        embed = disnake.Embed(
            title=f"Ошибка при создании мастер комнаты '{mr_name}'",
            description=f"Категория с ID '{category_id}' не найдена",
            color=0xFF0000
        )

        add_to_embed(embed)

        await ctx.send(embed=embed)
        return

    # Создание мастер комнаты в указанной категории
    master_channel = await category.create_voice_channel(name=f'➕ {mr_name}')

    # Сохранение значений в базу данных
    cursor.execute("INSERT INTO master_rooms (masterroom_id, default_name, u_ammount) VALUES (?, ?, ?)",
                   (master_channel.id, room_name, limit))
    connection.commit()

    embed = disnake.Embed(
        title=f"Мастер комната '{mr_name}' успешно создана!",
        description=f"Параметры мастер комнаты:",
        color=0x00FF00
    )
    embed.add_field(name="Категория мастер комнаты", value=category, inline=False)
    embed.add_field(name="Имена временных каналов", value=room_name, inline=False)
    if limit == 0:
        embed.add_field(name="Вместимость", value="Без ограничений", inline=False)
    else:
        embed.add_field(name="Вместимость", value=f"{limit} пользователей", inline=False)

    add_to_embed(embed)

    await ctx.send(embed=embed)

# Ивенты
@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

    ch_log = bot.get_channel(1122619319709335592)
    await ch_log.send(f"🤖Бот '{bot.user}' запущен и готов к работе")

    # Создание таблицы master_rooms, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS master_rooms (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        masterroom_id INTEGER,
                        default_name TEXT,
                        u_ammount INTEGER,
                        guild_id INTEGER
                    )''')

    # Создание таблицы temp_channels, если она не существует
    cursor.execute('''CREATE TABLE IF NOT EXISTS temp_channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        temp_id INTEGER
                    )''')

    connection.commit()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"{ctx.author}, у вас не достаточно прав для выполнения данной команды!")



@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None:
        masterroom_id = cursor.execute("SELECT masterroom_id FROM master_rooms WHERE masterroom_id=?",
                                       (after.channel.id,)).fetchone()
        if masterroom_id is not None:
            default_name = cursor.execute("SELECT default_name FROM master_rooms WHERE masterroom_id=?",
                                          (masterroom_id[0],)).fetchone()
            if default_name is not None:
                u_ammount = cursor.execute("SELECT u_ammount FROM master_rooms WHERE masterroom_id=?",
                                           (masterroom_id[0],)).fetchone()
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

    if before.channel is not None and before.channel.id in [temp[0] for temp in
                                                            cursor.execute("SELECT temp_id FROM temp_channels").fetchall()]:
        temp_channel = bot.get_channel(before.channel.id)
        if temp_channel is not None and len(temp_channel.voice_states) == 0:
            await asyncio.sleep(1)  # Задержка на 1 секунду
            await temp_channel.delete()
            cursor.execute("DELETE FROM temp_channels WHERE temp_id=?", (temp_channel.id,))
            connection.commit()


# Запуск бота
bot.run(TOKEN)
