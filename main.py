import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import AccentWord
import os

load_dotenv()
bot = Bot(token=os.getenv('TOKEN'))  # Connect Telegram bot
dp = Dispatcher(bot)


def init_db():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("HOST"),
            user=os.getenv("DB_USERNAME"),
            password=os.getenv("PASSWORD"),
            db=os.getenv("DATABASE")
        )

        if connection.is_connected():
            return connection
        else:
            raise Exception("Database is not connected")

    except Error as e:
        print("Error while connecting to MySQL", e)


mydb = init_db()


def get_cursor():
    global mydb
    try:
        mydb.ping(reconnect=True, attempts=3, delay=5)
    except mysql.connector.Error as err:
        mydb = init_db()
    return mydb.cursor()


def add_new_user_to_database(user_id, user_name):
    cursor = get_cursor()
    try:
        # Check if user exists
        data_query = (user_id,)
        query = ("select if( exists(select* from EgeBotUsers where TelegramUserID=%s), 1, 0)")
        cursor.execute(query, data_query)
        user_exist = cursor.fetchone()[0]

        # Add new user if he doesn't exist
        if not user_exist:
            query = ("insert into EgeBotUsers (TelegramUserID, Name) values (%s, %s)")
            data_query = (user_id, user_name)
            cursor = get_cursor()
            cursor.execute(query, data_query)
            mydb.commit()

    except Error as e:
        print(e)
    finally:
        cursor.close()


def update_score(user_id, amount):
    cursor = get_cursor()
    try:
        query = "SELECT Score FROM EgeBotUsers WHERE TelegramUserID = %s"
        data_query = (user_id,)
        cursor.execute(query, data_query)
        CurrentScore = cursor.fetchall()[0][0]  # Get current score
        NewScore = CurrentScore + amount  # Calculate new score

        sql = "UPDATE EgeBotUsers SET Score = %s WHERE TelegramUserID = %s"
        val = (NewScore, user_id)
        cursor.execute(sql, val)
        mydb.commit()  # Update DB Score

        return NewScore

    except Error as e:
        print(e)
    finally:
        cursor.close()


kb = [[types.KeyboardButton(text="🏆 Статистика"), types.KeyboardButton(text="🛠️ ТехПоддержка")]]
keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="")  # Create keyboard


@dp.message_handler(text="🛠️ ТехПоддержка")  # Run action after pressing keyboard
async def get_support(message: types.Message):
    await message.reply("🛠️ Связаться с ТехПоддержкой можно здесь: @NoveSupportBot")


def get_stats(user_id):
    cursor = get_cursor()
    try:
        sql = "SELECT * FROM EgeBotUsers ORDER BY Score DESC LIMIT 3"
        cursor.execute(sql)
        ChartStats = cursor.fetchall()

        query = "SELECT Score, Name FROM EgeBotUsers WHERE TelegramUserID = %s"
        data_query = (user_id,)
        cursor.execute(query, data_query)
        ChartStats.append(cursor.fetchall()[0])

        return ChartStats

    except Error as e:
        print(e)
    finally:
        cursor.close()


@dp.message_handler(text="🏆 Статистика")  # Run action after pressing keyboard
async def get_top(message: types.Message):
    loop = asyncio.get_event_loop()
    myresult = await loop.run_in_executor(None, get_stats, message.from_user.id)

    await message.reply('🏆 Топ игроков по очкам:\n'
                        f'\n🥇*{myresult[0][2]}* - `{myresult[0][3]}`'
                        f'\n🥈*{myresult[1][2]}* - `{myresult[1][3]}`'
                        f'\n🥉*{myresult[2][2]}* - `{myresult[2][3]}`'
                        f'\n\n*{myresult[3][1]}* (я) - `{myresult[3][0]}`'
                        , parse_mode="Markdown")


@dp.message_handler(commands=['start'])  # Run on /start command.
async def send_welcome(message: types.Message):
    dbname = message['from']["first_name"]
    if message['from']["last_name"] is not None:
        dbname += f" {message['from']['last_name'][0:1]}."

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, add_new_user_to_database, message.from_user.id, dbname)  # Add new user to database

    await bot.send_message(message.from_user.id, f"Привет, *{message.from_user.full_name}!*" +
                           '\n\nЯ - бот для повторения сложных случаев 4-го задания на ЕГЭ.' +
                           "\n\nНажми на слово, в котором верно поставлено ударение: ", parse_mode="Markdown",
                           reply_markup=keyboard)
    await send_game(message)


@dp.message_handler()
async def send_game(message: types.Message):
    dict = AccentWord.GenerateAccents()

    inline_kb_full = InlineKeyboardMarkup(row_width=2)
    i = len(dict['VariationsArray'])
    while i > 0:
        if i % 2 == 0:
            inline_kb_full.add(
                InlineKeyboardButton(dict['VariationsArray'][i - 1],
                                     callback_data=f"{dict['VariationsArray'][i - 1]}#{dict['CorrectWord']}"),
                InlineKeyboardButton(dict['VariationsArray'][i - 2],
                                     callback_data=f"{dict['VariationsArray'][i - 2]}#{dict['CorrectWord']}"),
            )
            i -= 2
        else:
            inline_kb_full.add(
                InlineKeyboardButton(dict['VariationsArray'][i - 1],
                                     callback_data=f"{dict['VariationsArray'][i - 1]}#{dict['CorrectWord']}"),
            )
            i -= 1

    await bot.send_message(message.chat.id, "💬 На какую букву ставится ударение в этом слове?", parse_mode="Markdown",
                           reply_markup=inline_kb_full)


@dp.callback_query_handler()
async def process_callback_button1(callback_query: types.CallbackQuery):
    M = callback_query.data.split("#")
    if M[0] == M[1]:
        loop = asyncio.get_event_loop()
        user_score = await loop.run_in_executor(None, update_score, callback_query["message"]["chat"]["id"], +10)

        await callback_query["message"].edit_text(text=f"✅ *{M[1]}*\n\n`+10` | Ваш счёт: `{user_score}`",
                                                  parse_mode="Markdown")
        try:
            await send_game(callback_query["message"])
        except:
            print("Failed to send a new game. Trying again...")
            await send_game(callback_query["message"])
    else:
        loop = asyncio.get_event_loop()
        user_score = await loop.run_in_executor(None, update_score, callback_query["message"]["chat"]["id"], -50)

        await callback_query["message"].edit_text(text=f"❌ Запомни: *{M[1]}*\n\n`-50` | Ваш счёт: `{user_score}`",
                                                  parse_mode="Markdown")
        try:
            await send_game(callback_query["message"])
        except:
            print("Failed to send a new game. Trying again...")
            await send_game(callback_query["message"])


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
