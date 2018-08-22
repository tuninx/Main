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
admin_username = 'CRAIDDO'

# username бота и/или человека, которые будут отправлять приказы
order_usernames = 'CRAIDDO'

# имя замка
castle_name = 'clover'

# путь к сокет файлу
socket_path = ''

# хост чтоб слушать telegram-cli
host = 'localhost'

# порт по которому слушать
port = 1338

# имя группы
group_name = ''

opts, args = getopt(sys.argv[1:], 'a:o:c:s:h:p:n', ['admin=', 'order=', 'castle=', 'socket=', 'host=', 'port=', 'group_name='])

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
    elif opt in ('-n', '--group_name'):
        group_name = arg



orders = {
    'ferma': '🍆',
    'mish': '🦇',
    'tortuga': '🐢',
    'roza': '🌹',
    'amber': '🍁',
    'skala': '🖤',
    'clover': '☘️',
    'def': '🛡Защита',
    'corovan': '/go'
}

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
get_info_diff = 360
hero_message_id = 0

bot_enabled = True
corovan_enabled = True
order_enabled = True


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
    global tz
    lt_info = 0
    # гребаная магия
    print(sender.contacts_search(bot_username))
    sleep(3)
    while True:
        try:
            if len(action_list):
                log('Отправляем ' + action_list[0])
                send_msg('@', bot_username, action_list.popleft())
            sleep_time = random.randint(2, 5)
            sleep(sleep_time)
        except Exception as err:
            log('Ошибка очереди: {0}'.format(err))


def parse_text(text, username, message_id):
    global hero_message_id
    global bot_enabled
    global corovan_enabled
    global tz
    global pref
    global msg_receiver
    if bot_enabled and username == bot_username:
        log('Получили сообщение от бота. Проверяем условия')

        if corovan_enabled and text.find(' пытается ограбить') != -1:
            sleep_time = random.randint(2, 15)
            sleep(sleep_time)
            action_list.append(orders['corovan'])
            mark_read('@', bot_username)
    else:
        if bot_enabled and order_enabled and username in order_usernames:
            if text.find(orders['ferma']) != -1:
                update_order(orders['ferma'])
            elif text.find(orders['mish']) != -1:
                update_order(orders['mish'])        
            elif text.find(orders['tortuga']) != -1:
                update_order(orders['tortuga'])
            elif text.find(orders['roza']) != -1:
                update_order(orders['roza'])
            elif text.find(orders['amber']) != -1:
                update_order(orders['amber'])
            elif text.find(orders['skala']) != -1:
                update_order(orders['skala'])
            elif text.find(orders['clover']) != -1:
                update_order(orders['clover'])
            elif text.find('🛡') != -1:
                update_order(castle)
            elif text.find('деф') != -1:
                update_order(castle)
            elif text.find('Деф') != -1:
                update_order(castle)  
                
        if username == admin_username:    
            if text == '#status':
                send_msg(pref, msg_receiver, '\n'.join([
                    '🤖Бот включен: {0}',
                    '🐫Корованы включены: {6}',
                    '🇪🇺Приказы включены: {8}',                   
                ]).format(bot_enabled, corovan_enabled, order_enabled))
                
def mark_read(pref, to):
    sender.mark_read(pref + to)
            
            
def send_msg(pref, to, message):
    sender.send_msg(pref + to, message)


def fwd(pref, to, message_id):
    sender.fwd(pref + to, message_id)

def update_order(order):
    current_order['order'] = order
    current_order['time'] = time()
    if order == castle:
        action_list.append(orders['def'])
    else:
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
