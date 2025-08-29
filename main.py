import discord
from discord.ext import commands
import aiohttp
import asyncio
import logging
import json
from datetime import datetime, timedelta
from aiohttp import web
import random

# Логи
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot.log',
    filemode='a'
)

# Настройки Discord
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix='$', intents=intents)
bot.remove_command("help")

# Настройки
CEREBRAS_API_KEY = "csk-2jkkrnwd68dx2fed2p4myf82xd4thvv28hcjk85wepjt43e2"  # Проверьте ключ!
DISCORD_BOT_TOKEN = "MTQxMDY1MzU0ODQ3OTI1MDYxNA.GS22BF.hPfBs61sZSqgemFNynCXcKya0u0sQSf4mvtxng"
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
BOT_API_KEY = "your_bot_api_key"
WARNINGS = {}
USER_MESSAGES = {}
ROLE_DURATION = 86400
ACTIVE_ROLE_NAME = "Легенда 228"
HELP_REMINDER_INTERVAL = 7200

# Вопросы для викторины
QUIZ_QUESTIONS = {
    "Какой цвет у неба в ясный день?": "Голубой",
    "Сколько лап у кошки?": "Четыре",
    "Как называется наш спутник?": "Луна",
    "Что растёт на дереве: яблоки или картошка?": "Яблоки",
    "Как зовут главного героя мультфильма 'Шрек'?": "Шрек"
}

# Загрузка предупреждений
def load_warnings():
    global WARNINGS
    try:
        with open('warnings.json', 'r') as f:
            WARNINGS = {int(k): v for k, v in json.load(f).items()}
        logging.info("Предупреждения загружены успешно")
    except FileNotFoundError:
        WARNINGS = {}
        logging.info("Файл warnings.json не найден, создан пустой словарь предупреждений")

# Сохранение предупреждений
def save_warnings():
    try:
        with open('warnings.json', 'w') as f:
            json.dump(WARNINGS, f)
        logging.info("Предупреждения сохранены")
    except Exception as e:
        logging.error(f"Ошибка при сохранении предупреждений: {e}")

# Загрузка статистики сообщений
def load_user_messages():
    global USER_MESSAGES
    try:
        with open('user_messages.json', 'r') as f:
            USER_MESSAGES = {int(k): v for k, v in json.load(f).items()}
        logging.info("Статистика сообщений загружена")
    except FileNotFoundError:
        USER_MESSAGES = {}
        logging.info("Файл user_messages.json не найден, создан пустой словарь")

# Сохранение статистики сообщений
def save_user_messages():
    try:
        with open('user_messages.json', 'w') as f:
            json.dump(USER_MESSAGES, f)
        logging.info("Статистика сообщений сохранена")
    except Exception as e:
        logging.error(f"Ошибка при сохранении статистики: {e}")

# Cerebras API
async def get_cerebras_response(prompt, is_retry=False, is_moderation=False):
    headers = {
        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "Ты ИИ-ассистент по имени Утырок228AI, дружелюбный, дерзкий и профессиональный. Отвечай на русском языке, чётко и по делу. "
        "Давай развёрнутые ответы (3-4 предложения), чтобы было понятно и интересно, но не затягивай. "
        "Иногда используй слово 'ништяк' для крутости и добавляй упоминания пельменей в ответы, чтобы было весело, например, 'Это ништяк, как свежие пельмени!'. "
        "Если вопрос простой, например 'привет', отвечай приветливо, например: 'Привет! Я Утырок228AI, готов помочь, что у тебя на уме? Это будет ништяк!'. "
        "Категорически запрещено обсуждать политику, религию, насилие, дискриминацию или любые другие чувствительные темы. "
        "Если вопрос затрагивает эти темы, вежливо откажись отвечать и предложи обсудить что-то другое, например: 'Прости, я не обсуждаю такие темы, давай лучше про пельмени или мемы!'. "
        "Если не знаешь ответа, признайся и предложи альтернативу. Завершай ответы логично, с точкой или восклицательным знаком."
    ) if not is_moderation else (
        "Ты модератор чата. Оцени, содержит ли переданный текст оскорбления, нецензурные слова, угрозы, политику, религию, дискриминацию или любой другой неподобающий контент. "
        "Верни **строго** JSON-объект с полями 'is_inappropriate' (true/false) и 'reason' (строка с причиной, если is_inappropriate=true, иначе пустая строка). "
        "Пример: {\"is_inappropriate\": true, \"reason\": \"Сообщение содержит нецензурные слова\"} или {\"is_inappropriate\": false, \"reason\": \"\"}. "
        "Не возвращай ничего, кроме JSON-объекта, и убедись, что ключи заключены в двойные кавычки."
    )
    data = {
        "model": "llama3.1-8b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_completion_tokens": 1000 if not is_moderation else 100,
        "temperature": 0.8 if not is_moderation else 0.3,
        "top_p": 0.9,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(CEREBRAS_API_URL, json=data, headers=headers, timeout=15) as response:
                response_text = await response.text()
                logging.info(f"Ответ от Cerebras API: {response_text}")
                response.raise_for_status()
                logging.info(f"Остаток лимита API: {response.headers.get('X-RateLimit-Remaining')}")
                result = await response.json()
                response_text = result["choices"][0]["message"]["content"].strip()
                if is_moderation:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logging.error(f"Ошибка парсинга JSON от Cerebras: {response_text}, ошибка: {e}")
                        if not is_retry:
                            retry_prompt = f"Проанализируй этот текст: '{prompt}'. Верни **строго** JSON: {{\"is_inappropriate\": true/false, \"reason\": \"причина или пустая строка\"}}."
                            return await get_cerebras_response(retry_prompt, is_retry=True, is_moderation=True)
                        return {"is_inappropriate": False, "reason": "Ошибка обработки ответа от API"}
                if len(response_text.split()) < 5 and not is_retry:
                    logging.warning(f"Ответ слишком короткий: {response_text}, пробуем доработать")
                    retry_prompt = f"Дай более полный ответ на '{prompt}' в том же дружелюбном стиле, добавь 2-3 предложения. Не обсуждай политику, религию, насилие или дискриминацию."
                    return await get_cerebras_response(retry_prompt, is_retry=True)
                return response_text
    except aiohttp.ClientConnectorError as e:
        logging.error(f"Ошибка соединения с Cerebras API: {e}")
        return "Ой, не могу связаться с сервером! Проверь интернет и попробуй снова."
    except aiohttp.ClientResponseError as e:
        if e.status == 401:
            logging.error(f"Ошибка авторизации в Cerebras API: {e}")
            return "Ошибка авторизации API. Проверь ключ API!"
        if e.status == 429:
            logging.warning("Превышен лимит API. Ждем 10 секунд.")
            await asyncio.sleep(10)
            return "Слишком много запросов! Подожди немного и попробуй снова."
        logging.error(f"Ошибка API: {e}")
        return "Что-то пошло не так с API. Попробуй снова через минуту!"
    except asyncio.TimeoutError:
        logging.error("Таймаут запроса к Cerebras API")
        return "Сервер отвечает слишком долго. Попробуй ещё раз!"

# Проверка на плохие слова
async def check_bad_words(message):
    if len(message.content) < 5:
        return False
    moderation_result = await get_cerebras_response(message.content, is_moderation=True)
    if not isinstance(moderation_result, dict) or 'is_inappropriate' not in moderation_result:
        logging.error(f"Ошибка: Cerebras не вернул ожидаемый JSON для модерации: {moderation_result}")
        return False
    
    if moderation_result['is_inappropriate']:
        await message.delete()
        user_id = message.author.id
        WARNINGS[user_id] = WARNINGS.get(user_id, 0) + 1
        warning_count = WARNINGS[user_id]
        save_warnings()
        
        reason = moderation_result.get('reason', 'Неподобающий контент (политика, религия или другое)')
        logging.info(f"Сообщение от {message.author} удалено: {reason}. Предупреждений: {warning_count}")
        
        await message.channel.send(
            f"{message.author.mention}, твое сообщение удалено за {reason}. "
            f"Это предупреждение #{warning_count}. "
            f"Давай без политики, религии и прочих скользких тем, договорились? Пельмени лучше! 😎"
        )
        return True
    return False

# Команда $chat
@bot.command()
async def chat(ctx, *, text):
    if not text:
        await ctx.send("Пожалуйста, напиши что-нибудь после $chat, чтобы я мог ответить! Это будет ништяк!")
        return
    
    # Проверка текста на запрещённые темы перед отправкой в API
    moderation_result = await get_cerebras_response(text, is_moderation=True)
    if moderation_result.get('is_inappropriate', False):
        reason = moderation_result.get('reason', 'Неподобающий контент')
        await ctx.send(
            f"{ctx.author.mention}, твой вопрос содержит {reason}. "
            "Я не обсуждаю политику, религию, насилие или дискриминацию. "
            "Давай лучше про пельмени или что-нибудь ништяковое! 😎"
        )
        return
    
    response = await get_cerebras_response(text)
    await ctx.send(response)

# HTTP-эндпоинт для команд
async def handle_command(request):
    data = await request.json()
    logging.info(f"Получен запрос на /command: {data}")
    if data.get("api_key") != BOT_API_KEY:
        logging.error(f"Неверный API-ключ: {data.get('api_key')}")
        return web.json_response({"error": "Неверный API-ключ"}, status=401)
    
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    action = data.get("action")
    reason = data.get("reason", "Нарушение правил")
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        logging.error(f"Сервер {guild_id} не найден")
        return web.json_response({"error": "Сервер не найден"}, status=404)
    
    member = guild.get_member(int(user_id))
    if not member:
        logging.error(f"Пользователь {user_id} не найден на сервере {guild_id}")
        return web.json_response({"error": "Пользователь не найден"}, status=404)
    
    try:
        if action == "warn":
            channel = guild.text_channels[0]
            await channel.send(f"{member.mention} получил предупреждение за: {reason}. Ништяк, веди себя как пельмени — вкусно и без проблем! 😎")
            logging.info(f"Предупреждение выдано: {member} за {reason}")
            return web.json_response({"message": f"Предупреждение выдано {member.name}"})
        else:
            logging.error(f"Неверное действие: {action}")
            return web.json_response({"error": "Неверное действие"}, status=400)
    except discord.Forbidden:
        logging.error(f"Нет прав для выполнения действия {action} для {member}")
        return web.json_response({"error": "Нет прав для выполнения действия"}, status=403)
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды: {e}")
        return web.json_response({"error": str(e)}, status=500)

# Запуск HTTP-сервера
async def start_http_server():
    app = web.Application()
    app.add_routes([web.post('/command', handle_command)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    logging.info("HTTP-сервер запущен на порту 8000")

# Приветствие при добавлении на сервер
@bot.event
async def on_guild_join(guild):
    channel = guild.system_channel or discord.utils.get(guild.text_channels, name="general")
    if channel and channel.permissions_for(guild.me).send_messages:
        await channel.send(
            "Йо, народ! Я **Утырок228AI**, дерзкий бот, готовый жечь мемы и раздавать ништяк! 😎 "
            "Мои команды:\n"
            "- `$chat <текст>` — задай любой вопрос, я отвечу!\n"
            "- `$warn @user [причина]` — выдать предупреждение (для модераторов).\n"
            "- `$game quiz` — запустить викторину!\n"
            "- `$meme` — сгенерировать мем или шутку.\n"
            "Пиши активно, и за 100 сообщений получишь роль **Легенда 228** на 24 часа! Ништяк, как пельмени! 🥟 "
            "Напиши `$help`, чтобы узнать всё ещё раз!"
        )
        logging.info(f"Бот добавлен на сервер {guild.name} (ID: {guild.id})")

# Периодическое напоминание о командах
async def help_reminder():
    await bot.wait_until_ready()
    while not bot.is_closed():
        for guild in bot.guilds:
            channel = guild.system_channel or discord.utils.get(guild.text_channels, name="general")
            if channel and channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    "Эй, народ! Не забывайте про мои ништяковые команды! 😎\n"
                    "- `$chat <текст>` — задай вопрос, я отвечу!\n"
                    "- `$warn @user [причина]` — предупреждение (для модераторов).\n"
                    "- `$game quiz` — викторина для крутых!\n"
                    "- `$meme` — мемы, как горячие пельмени! 🥟\n"
                    "За 100 сообщений получишь роль **Легенда 228** на 24 часа! Погнали!"
                )
                logging.info(f"Напоминание о командах отправлено на сервер {guild.name}")
        await asyncio.sleep(HELP_REMINDER_INTERVAL)

# Бот готов
@bot.event
async def on_ready():
    load_warnings()
    load_user_messages()
    logging.info(f'Бот {bot.user} готов! Подключен к {len(bot.guilds)} серверам')
    try:
        with open('bot_status.txt', 'w') as f:
            f.write(f"{bot.user}|Активен|{len(bot.guilds)}")
    except Exception as e:
        logging.error(f"Ошибка записи статуса: {e}")
    bot.loop.create_task(help_reminder())

# Обработка сообщений
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    user_id = message.author.id
    USER_MESSAGES[user_id] = USER_MESSAGES.get(user_id, 0) + 1
    save_user_messages()

    if USER_MESSAGES[user_id] >= 100:
        role = discord.utils.get(message.guild.roles, name=ACTIVE_ROLE_NAME)
        if role and role not in message.author.roles:
            try:
                await message.author.add_roles(role)
                await message.channel.send(f"🎉 {message.author.mention}, ты получил временную роль **{ACTIVE_ROLE_NAME}** за 100 сообщений! Утырок228AI говорит: 'Ништяк, как пельмени!' 😎 Роль снимется через 24 часа.")
                logging.info(f"Временная роль {ACTIVE_ROLE_NAME} выдана {message.author}")
                bot.loop.create_task(remove_role_after_delay(message.author, role))
            except discord.Forbidden:
                logging.error(f"Ошибка: Нет прав для выдачи роли {message.author}")

    if await check_bad_words(message):
        return

    await bot.process_commands(message)

# Функция для удаления роли через задержку
async def remove_role_after_delay(member, role):
    await asyncio.sleep(ROLE_DURATION)
    try:
        await member.remove_roles(role)
        logging.info(f"Роль {role.name} снята с {member} после {ROLE_DURATION} секунд")
    except discord.Forbidden:
        logging.error(f"Ошибка: Нет прав для снятия роли с {member}")

# Команды бота
@bot.command()
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason="Нарушение правил"):
    await ctx.send(f"{member.mention} получил предупреждение за: {reason}. Ништяк, веди себя как пельмени — вкусно и без проблем! 😎")
    logging.info(f"Предупреждение выдано: {member} за {reason}")

@bot.command()
async def help(ctx):
    await ctx.send(
        "Привет! Вот что я умею:\n"
        "- `$chat <текст>` — задай любой вопрос, я отвечу!\n"
        "- `$warn @user [причина]` — выдать предупреждение (для модераторов).\n"
        "- `$game quiz` — запустить викторину!\n"
        "- `$meme` — сгенерировать мем или шутку.\n"
        "Пиши активно, и за 100 сообщений получишь роль **Легенда 228** на 24 часа! Ништяк, как пельмени! 😎"
    )

@bot.command()
async def game(ctx, game_type="quiz"):
    if game_type.lower() == "quiz":
        question, answer = random.choice(list(QUIZ_QUESTIONS.items()))
        await ctx.send(f"🎲 Викторина от Утырок228AI! Вопрос: **{question}** Напиши ответ в чат! (30 секунд на ответ)")
        
        def check(m):
            return m.channel == ctx.channel and m.author != bot.user
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=30.0)
            if msg.content.lower() == answer.lower():
                await ctx.send(f"🎉 {msg.author.mention}, ты прав! Это **{answer}**! Получай +1 балл крутости! Ништяк, как пельмени! 😎")
            else:
                await ctx.send(f"😬 {msg.author.mention}, неверно! Правильный ответ: **{answer}**. Попробуй ещё раз!")
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Время вышло! Ответ был: **{answer}**. Напиши `$game quiz`, чтобы сыграть ещё!")

@bot.command()
async def meme(ctx):
    prompt = "Сгенерируй короткую, смешную шутку в стиле дерзкого русского мемного бота по имени Утырок228AI. Используй 'ништяк' и упомяни пельмени."
    response = await get_cerebras_response(prompt)
    await ctx.send(f"😎 Утырок228AI жжёт: {response}")

# Обработка ошибок команд
@warn.error
async def warn_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("У тебя недостаточно прав для выдачи предупреждений.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Укажи пользователя! Например: $warn @user причина")

# Запуск бота и HTTP-сервера
async def main():
    try:
        await start_http_server()
        await bot.start(DISCORD_BOT_TOKEN)
    except Exception as e:
        logging.error(f"Ошибка запуска: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")