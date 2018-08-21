# coding=utf-8
from pytg.sender import Sender
from pytg.receiver import Receiver
from pytg.utils import coroutine
from collections import deque
from time import time, sleep
from getopt import getopt
from datetime import datetime
import sys
import re
import _thread
import random
import pytz

# username игрового бота
bot_username = 'keeketheone'

# ваш username или username человека, который может отправлять запросы этому скрипту
admin_username = ''

# username бота и/или человека, которые будут отправлять приказы
order_usernames = ''

# имя замка
castle_name = 'blue'


# путь к сокет файлу
socket_path = ''

# хост чтоб слушать telegram-cli
host = 'localhost'

# порт по которому слушать
port = 1338

# скидывание денег покупкой/продажей шлемов
donate_buying = False

# включить прокачку при левелапе
lvl_up = 'lvl_off'

# имя группы
group_name = ''

opts, args = getopt(sys.argv[1:], 'a:o:c:s:h:p:g:b:l:n', ['admin=', 'order=', 'castle=', 'socket=', 'host=', 'port=',
                                                          'gold=', 'buy=', 'lvlup=', 'group_name='])

for opt, arg in opts:
    if opt in ('-a', '--admin'):
        admin_username = arg
    elif opt in ('-o', '--order'):
        order_usernames = arg.split(',')
    elif opt in ('-c', '--castle'):
        castle_name = arg
    elif opt in ('-s', '--socket'):
        socket_path = arg
    elif opt in ('-h', '--host'):
        host = arg
    elif opt in ('-p', '--port'):
        port = int(arg)
    elif opt in ('-g', '--gold'):
        gold_to_left = int(arg)
    elif opt in ('-b', '--buy'):
        donate_buying = bool(arg)
    elif opt in ('-l', '--lvlup'):
        lvl_up = arg
    elif opt in ('-n', '--group_name'):
        group_name = arg



orders = {
    'red': '🇮🇲',
    'black': '🇬🇵',
    'white': '🇨🇾',
    'yellow': '🇻🇦',
    'blue': '🇪🇺',
    'mint': '🇲🇴',
    'twilight': '🇰🇮',
    'lesnoi_fort': '🌲Лесной форт',
    'les': '🌲Лес',
    'gorni_fort': '⛰Горный форт',
    'gora': '⛰',
    'cover': '🛡 Защита',
    'attack': '⚔ Атака',
    'cover_symbol': '🛡',
    'hero': '🏅Герой',
    'corovan': '/go',
    'peshera': '🕸Пещера',
    'quests': '🗺 Квесты',
    'lvl_def': '+1 🛡Защита',
    'lvl_atk': '+1 ⚔️Атака',
    'lvl_off': 'Выключен'
}


arena_cover = ['🛡головы', '🛡корпуса', '🛡ног']
arena_attack = ['🗡в голову', '🗡по корпусу', '🗡по ногам']
# поменять blue на red, black, white, yellow в зависимости от вашего замка
castle = orders[castle_name]
# текущий приказ на атаку/защиту, по умолчанию всегда защита, трогать не нужно
current_order = {'time': 0, 'order': castle}
# задаем получателя ответов бота: админ или группа
if group_name =='':
    pref = '@'
    msg_receiver = admin_username
else:
    pref = ''
    msg_receiver = group_name

sender = Sender(sock=socket_path) if socket_path else Sender(host=host,port=port)
action_list = deque([])
log_list = deque([], maxlen=30)
lt_arena = 0
get_info_diff = 360
hero_message_id = 0
last_captcha_id = 0
gold_to_left = 0

bot_enabled = True
arena_enabled = False
les_enabled = False
peshera_enabled = False
corovan_enabled = True
order_enabled = False
auto_def_enabled = False
donate_enabled = False
quest_fight_enabled = False

arena_running = False
arena_delay = False
arena_delay_day = -1
tz = pytz.timezone('Europe/Moscow')

@coroutine
def work_with_message(receiver):
    while True:
        msg = (yield)
        try:
            if msg['event'] == 'message' and 'text' in msg and msg['peer'] is not None:
                # Проверяем наличие юзернейма, чтобы не вываливался Exception
                if 'username' in msg['sender']:
                    parse_text(msg['text'], msg['sender']['username'], msg['id'])
        except Exception as err:
            log('Ошибка coroutine: {0}'.format(err))


def queue_worker():
    global get_info_diff
    global arena_delay
    global arena_delay_day
    global tz
    lt_info = 0
    # гребаная магия
    print(sender.contacts_search(bot_username))
    sleep(3)
    while True:
        try:
            if time() - lt_info > get_info_diff:
                if arena_delay and arena_delay_day != datetime.now(tz).day:
                    arena_delay = False
                lt_info = time()
                get_info_diff = random.randint(12600, 14400)
                if bot_enabled:
                    send_msg('@', bot_username, orders['hero'])
                continue

            if len(action_list):
                log('Отправляем ' + action_list[0])
                send_msg('@', bot_username, action_list.popleft())
            sleep_time = random.randint(2, 5)
            sleep(sleep_time)
        except Exception as err:
            log('Ошибка очереди: {0}'.format(err))


def parse_text(text, username, message_id):
    global lt_arena
    global hero_message_id
    global bot_enabled
    global arena_enabled
    global les_enabled
    global peshera_enabled
    global corovan_enabled
    global order_enabled
    global auto_def_enabled
    global donate_enabled
    global donate_buying
    global last_captcha_id
    global arena_delay
    global arena_delay_day
    global tz
    global arena_running
    global lvl_up
    global pref
    global msg_receiver
    global quest_fight_enabled
    if bot_enabled and username == bot_username:
        log('Получили сообщение от бота. Проверяем условия')

        if corovan_enabled and text.find(' пытается ограбить') != -1:
            action_list.append(orders['corovan'])

            # Вкл/выкл бота
            elif text == '#enable_bot':
                bot_enabled = True
                send_msg(pref, msg_receiver, 'Бот успешно включен')
            elif text == '#disable_bot':
                bot_enabled = False
                send_msg(pref, msg_receiver, 'Бот успешно выключен')

            # Вкл/выкл арены
            elif text == '#enable_arena':
                arena_enabled = True
                send_msg(pref, msg_receiver, 'Арена успешно включена')
            elif text == '#disable_arena':
                arena_enabled = False
                send_msg(pref, msg_receiver, 'Арена успешно выключена')

            # Вкл/выкл леса
            elif text == '#enable_les':
                les_enabled = True
                send_msg(pref, msg_receiver, 'Лес успешно включен')
            elif text == '#disable_les':
                les_enabled = False
                send_msg(pref, msg_receiver, 'Лес успешно выключен')

            # Вкл/выкл пещеры
            elif text == '#enable_peshera':
                peshera_enabled = True
                send_msg(pref, msg_receiver, 'Пещеры успешно включены')
            elif text == '#disable_peshera':
                peshera_enabled = False
                send_msg(pref, msg_receiver, 'Пещеры успешно выключены')

            # Вкл/выкл корована
            elif text == '#enable_corovan':
                corovan_enabled = True
                send_msg(pref, msg_receiver, 'Корованы успешно включены')
            elif text == '#disable_corovan':
                corovan_enabled = False
                send_msg(pref, msg_receiver, 'Корованы успешно выключены')

            # Вкл/выкл команд
            elif text == '#enable_order':
                order_enabled = True
                send_msg(pref, msg_receiver, 'Приказы успешно включены')
            elif text == '#disable_order':
                order_enabled = False
                send_msg(pref, msg_receiver, 'Приказы успешно выключены')

            # Вкл/выкл авто деф
            elif text == '#enable_auto_def':
                auto_def_enabled = True
                send_msg(pref, msg_receiver, 'Авто деф успешно включен')
            elif text == '#disable_auto_def':
                auto_def_enabled = False
                send_msg(pref, msg_receiver, 'Авто деф успешно выключен')

            # Вкл/выкл авто донат
            elif text == '#enable_donate':
                donate_enabled = True
                send_msg(pref, msg_receiver, 'Донат успешно включен')
            elif text == '#disable_donate':
                donate_enabled = False
                send_msg(pref, msg_receiver, 'Донат успешно выключен')

            # Вкл/выкл донат в лавку
            elif text == '#enable_buy':
                donate_buying = True
                send_msg(pref, msg_receiver, 'Донат в лавку успешно включен')
            elif text == '#disable_buy':
                donate_buying = False
                send_msg(pref, msg_receiver, 'Донат в лавку успешно выключен')

            # Вкл/выкл битву по время квеста
            elif text == '#enable_quest_fight':
                quest_fight_enabled = True
                send_msg(pref, msg_receiver, 'Битва включена')
            elif text == '#disable_quest_fight':
                quest_fight_enabled = False
                send_msg(pref, msg_receiver, 'Битва отключена')

            # что качать при левелапе
            elif text == '#lvl_atk':
                lvl_up = 'lvl_atk'
                send_msg(pref, msg_receiver, 'Качаем атаку')
            elif text == '#lvl_def':
                lvl_up = 'lvl_def'
                send_msg(pref, msg_receiver, 'Качаем защиту')
            elif text == '#lvl_off':
                lvl_up = 'lvl_off'
                send_msg(pref, msg_receiver, 'Не качаем ничего')

            # Получить статус
            elif text == '#status':
                send_msg(pref, msg_receiver, '\n'.join([
                    '🤖Бот включен: {0}',
                    '📯Арена включена: {1}',
                    '🔎Сейчас на арене: {2}',
                    '🌲Лес включен: {3}',
                    '🕸Пещеры включены: {4}',
                    '🐫Корованы включены: {5}',
                    '🇪🇺Приказы включены: {6}',
                    '🛡Авто деф включен: {7}',
                    '💰Донат включен: {8}',
                    '🏚Донат в лавку вместо казны: {9}',
                    '🌟Левелап: {10}',
                ]).format(bot_enabled, arena_enabled, arena_running, les_enabled, peshera_enabled, corovan_enabled, order_enabled, 
                          auto_def_enabled, donate_enabled, donate_buying,orders[lvl_up]))

            # Информация о герое
            elif text == '#hero':
                if hero_message_id == 0:
                    send_msg(pref, msg_receiver, 'Информация о герое пока еще недоступна')
                else:
                    fwd(pref, msg_receiver, hero_message_id)

            # Получить лог
            elif text == '#log':
                send_msg(pref, msg_receiver, '\n'.join(log_list))
                log_list.clear()

            elif text == '#lt_arena':
                send_msg(pref, msg_receiver, str(lt_arena))

            elif text == '#order':
                text_date = datetime.fromtimestamp(current_order['time']).strftime('%Y-%m-%d %H:%M:%S')
                send_msg(pref, msg_receiver, current_order['order'] + ' ' + text_date)

            elif text == '#time':
                text_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                send_msg(pref, msg_receiver, text_date)

            elif text == '#ping':
                send_msg(pref, msg_receiver, '#pong')

            elif text == '#get_info_diff':
                send_msg(pref, msg_receiver, str(get_info_diff))

            elif text.startswith('#push_order'):
                command = text.split(' ')[1]
                if command in orders:
                    update_order(orders[command])
                    send_msg(pref, msg_receiver, 'Команда ' + command + ' применена')
                else:
                    send_msg(pref, msg_receiver, 'Команда ' + command + ' не распознана')

            elif text.startswith('#captcha'):
                command = text.split(' ')[1]
                if command in captcha_answers:
                    action_list.append(captcha_answers[command])
                    bot_enabled = True
                    send_msg('@', admin_username, 'Команда ' + command + ' применена')
                else:
                    send_msg('@', admin_username, 'Команда ' + command + ' не распознана')


def send_msg(pref, to, message):
    sender.send_msg(pref + to, message)


def fwd(pref, to, message_id):
    sender.fwd(pref + to, message_id)


def update_order(order):
    current_order['order'] = order
    current_order['time'] = time()
    if order == castle:
        action_list.append(orders['cover'])
    else:
        action_list.append(orders['attack'])
    action_list.append(order)


def log(text):
    message = '{0:%Y-%m-%d %H:%M:%S}'.format(datetime.now()) + ' ' + text
    print(message)
    log_list.append(message)


if __name__ == '__main__':
    receiver = Receiver(sock=socket_path) if socket_path else Receiver(port=port)
    receiver.start()  # start the Connector.
    _thread.start_new_thread(queue_worker, ())
    receiver.message(work_with_message(receiver))
    receiver.stop()
