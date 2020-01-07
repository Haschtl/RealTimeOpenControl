import time
from threading import Thread
# from io import BytesIO
import urllib.request

import json
from telegram.ext import MessageHandler, CommandHandler, CallbackQueryHandler, Filters, Updater
from telegram import KeyboardButton, ReplyKeyboardMarkup, ChatAction, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)

import os
import traceback
import psutil
import datetime as dt
# import copy

import logging as log
log.basicConfig(level=log.DEBUG)
logging = log.getLogger(__name__)

try:
    import matplotlib.pyplot as plt
    from matplotlib.pyplot import text as plt_text
    import matplotlib.dates as mdates

    years = mdates.YearLocator()   # every year
    months = mdates.MonthLocator()  # every month
    yearsFmt = mdates.DateFormatter('%Y')

except (ImportError, SystemError):
    logging.warning(
        'Could not import matplotlib.pyplot\nThis happens if matplotlib or tkinker isn\'t installed. \nReceiving plots via telegram is disabled.')
    plt = None

# Bot.answer_callback_query(callback_query_id, text=None, show_alert=False, url=None, cache_time=None, timeout=None, **kwargs) for sharing
# Bot.delete_message(chat_id, message_id, timeout=None, **kwargs)


if True:
    try:
        from PyQt5.QtCore import QCoreApplication

        translate = QCoreApplication.translate
    except ImportError:
        def translate(id, text):
            return text
    def _(text):
        return translate('web', text)
else:
    import gettext
    _ = gettext.gettext


__imports__ = ['python-telegram-bot']

DPI = 300
WELCOME_MESSAGE = False


class telegramBot():
    """
    This class handles the communication with telegram-clients.
    """

    def __init__(self, logger):
        self.BACKBUTTON = '\u2190'+translate('RTOC', ' Back')
        self.logger = logger
        self.telegram_clients = {}
        self.loadClients()
        self.selectedSignalForEvent = None
        self.servername = self.logger.config['global']['name']
        self.token = self.logger.config['telegram']['token']
        self.updater = None
        self.current_plugin = {}
        self.current_call = {}
        self.last_messages = {}
        self.bot = None
        self.signals_selected = {}
        self.signals_range = {}
        self.helper = {}
        self._teleThreads = []
        self.busy = False
        self._pluginCall_chat_id = None
        self.menuCommands = [translate('RTOC', 'Latest values'), translate('RTOC', 'Signals'), translate('RTOC', 'Settings')]
        self.writeMenuCommands = [translate('RTOC', 'Devices'), translate('RTOC', 'Create Event/Signal'), translate('RTOC', 'Automation')]
        self.adjustEventNotificationCommands = [translate('RTOC', "No notifications"), translate('RTOC', "Only errors"), translate('RTOC', "Warnings"), translate('RTOC', "All events")]

    def setToken(self, token):
        self.token = token
        self.logger.config['telegram']['token'] = token

    def saveClients(self):
        with open(self.logger.config['global']['documentfolder']+"/telegram_clients.json", 'w', encoding="utf-8") as fp:
            json.dump(self.telegram_clients, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def loadClients(self):
        self.telegram_clients = {}
        if 'chat_ids' in self.logger.config['telegram'].keys():
            self.telegram_clients = self.logger.config['telegram']['chat_ids']
            self.logger.config['telegram'].pop('chat_ids')

        userpath = self.logger.config['global']['documentfolder']
        if not os.path.exists(userpath):
            os.mkdir(userpath)
        if os.path.exists(userpath+"/telegram_clients.json"):
            try:
                with open(userpath+"/telegram_clients.json", encoding="UTF-8") as jsonfile:
                    self.telegram_clients = json.load(jsonfile, encoding="UTF-8")
            except Exception:
                self.telegram_clients = {}
                logging.error('Error in Telegram_Clients-JSON-File')
                return
        else:
            self.telegram_clients = {}
            if 'chat_ids' in self.logger.config['telegram'].keys():
                self.telegram_clients = self.logger.config['telegram']['chat_ids']
                self.logger.config['telegram'].pop('chat_ids')
            return

    def check_chat_id(self, chat_id):
        if self.bot == None:
            return
        if chat_id is not None:
            if str(chat_id) not in list(self.telegram_clients.keys()):
                print('new telegram client connected')
                chat = self.bot.get_chat(chat_id)
                first_name = str(chat.first_name)
                last_name = str(chat.last_name)
                text = translate('RTOC', '{} {} joined {} for the first time.').format(first_name, last_name, self.logger.config['global']['name'])
                self.send_message_to_all(text, permission='admin')
                logging.info('TELEGRAM BOT: New client connected with ID: '+str(chat_id))
                if len(self.telegram_clients.keys()) == 0:
                    ad = 'admin'
                else:
                    ad = self.logger.config['telegram']['default_permission']
                user = {'eventlevel': self.logger.config['telegram']['default_eventlevel'], 'shortcuts':[[], []], 'permission':ad, 'first_name': first_name, 'last_name': last_name, 'menu': 'menu', 'preview': False}
                self.telegram_clients[str(chat_id)] = user
                self.saveClients()
            elif type(self.telegram_clients[str(chat_id)]) != dict:
                print(self.telegram_clients[str(chat_id)])
                print('old telegram client updated')
                chat = self.bot.get_chat(chat_id)
                first_name = str(chat.first_name)
                last_name = str(chat.last_name)
                # Transform old style to new style
                evLevel = self.telegram_clients[str(chat_id)][0]
                shortcuts = self.telegram_clients[str(chat_id)][1]
                user = {'eventlevel':evLevel,'shortcuts':shortcuts,'permission':'write', 'first_name': first_name, 'last_name': last_name}
                self.telegram_clients[str(chat_id)] = user
            elif type(self.telegram_clients[str(chat_id)]) == dict:
                if 'admin' in self.telegram_clients[str(chat_id)].keys():
                    ad = self.telegram_clients[str(chat_id)]['admin']
                    if ad:
                        ad = 'admin'
                    else:
                        ad = 'write'
                    self.telegram_clients[str(chat_id)].pop('admin')
                    self.telegram_clients[str(chat_id)]['permission'] = ad

            if 'menu' not in self.telegram_clients[str(chat_id)].keys():
                self.telegram_clients[str(chat_id)]['menu'] = 'menu'
                self.saveClients()
            if 'preview' not in self.telegram_clients[str(chat_id)].keys():
                self.telegram_clients[str(chat_id)]['preview'] = False
            if chat_id not in self.current_plugin.keys():
                self.current_plugin[chat_id] = ''
                self.current_call[chat_id] = ''
                self.helper[chat_id] = None
                self.signals_selected[chat_id] = []
                self.signals_range[chat_id] = [time.time()-60*60*24,time.time()]

    def sendEvent(self, message, devicename, signalname, priority):
        ptext = [translate('RTOC','_Information_'), translate('RTOC','*Warning*'), translate('RTOC','*_Error_*')][priority]
        message = translate('RTOC', '{} from {}.{}:\n{}').format(ptext, devicename, signalname, message)
        for id in self.telegram_clients.keys():
            self.check_chat_id(id)
            if priority >= self.telegram_clients[id]['eventlevel'] and self.telegram_clients[id]['permission'] in ['read', 'write','admin']:
                self.send_message(chat_id=int(id), text=message, delete=False)
                # try:
                #     self.bot.send_message(chat_id=int(id), text=message,
                #                           parse_mode=ParseMode.MARKDOWN)
                # except Exception:
                #     self.bot.send_message(chat_id=int(id), text=message)

    def check_permission_and_priority(self, chat_id, priority, permission):
        self.check_chat_id(chat_id)
        perms = ['blocked','custom','read','write','admin']
        if priority >= self.telegram_clients[chat_id]['eventlevel']:
            if permission in perms:
                idx = perms.index(self.telegram_clients[chat_id]['permission'])
                idx2 = perms.index(permission)
                if idx >= idx2:
                    return True
        return False


    def send_message_to_all(self, message, priority=0, permission='write', chat_ids=None):
        if self._pluginCall_chat_id is not None:
            chat_ids = [self._pluginCall_chat_id]
        if chat_ids is None:
            chat_ids = []
            for id in self.telegram_clients.keys():
                if self.check_permission_and_priority(id, priority, permission):
                    chat_ids.append(id)

        for id in chat_ids:
            self.send_message(chat_id=int(id), text=message, delete=False)

    def send_photo(self, path, priority=0, permission='write', chat_ids=None):
        if self.bot == None:
            return
        if self._pluginCall_chat_id is not None:
            chat_ids = [self._pluginCall_chat_id]
        if chat_ids == None:
            chat_ids = []
            for id in self.telegram_clients.keys():
                if self.check_permission_and_priority(id, priority, permission):
                    chat_ids.append(id)

        for id in chat_ids:
            try:
                self.bot.send_photo(chat_id=int(id), photo=open(path, 'rb'))
            except Exception as error:
                text = translate('RTOC', 'Error while sending photo:\n{}').format(error)
                self.send_message(id, text)

    def send_document(self, path, priority=0, permission='write', chat_ids=None):
        if self.bot == None:
            return
        if self._pluginCall_chat_id is not None:
            chat_ids = [self._pluginCall_chat_id]
        if chat_ids == None:
            chat_ids = []
            for id in self.telegram_clients.keys():
                if self.check_permission_and_priority(id, priority, permission):
                    chat_ids.append(id)

        for id in chat_ids:
            try:
                self.bot.send_document(chat_id=int(id), photo=open(path, 'rb'))
            except Exception as error:
                text = translate('RTOC', 'Error while sending file:\n{}').format(error)
                self.send_message(id, text)

    def send_plot(self, signals={}, title='', text='', events=[], dpi=300, priority=0, permission='write', chat_ids=None):
        if self.bot == None:
            return
        if self._pluginCall_chat_id is not None:
            chat_ids = [self._pluginCall_chat_id]
        plt.gcf().clear()
        ymax = 0
        ymin = 0
        if type(signals) == dict:
            for name in signals.keys():
                if type(signals[name])==list:
                    if len(signals[name])==2:
                        if len(signals[name][0]) == len(signals[name][1]):
                            signal = signals[name]

                            if max(signal[1]) > ymax:
                                ymax = max(signal[1])
                            if min(signal[1]) > ymin:
                                ymin = min(signal[1])
                            try:
                                #dates = [dt.datetime.fromtimestamp(float(ts)) for ts in list(signal[2])]
                                dates = []
                                for ts in list(signal[0]):
                                    if type(ts) == list:
                                        print(ts)
                                    dates.append(dt.datetime.fromtimestamp(float(ts)))
                                if abs(signal[0][0]-signal[0][-1]) > 5*60:
                                    xfmt = mdates.DateFormatter(translate('RTOC', '%d.%m %H:%M'))
                                else:
                                    xfmt = mdates.DateFormatter(translate('RTOC', '%d.%m %H:%M:%S'))
                                plt.plot(dates, list(signal[1]), label=name)  # ,'-x')
                            except Exception as error:
                                print(error)
                                print(traceback.format_exc())
                                logging.error(traceback.format_exc())

            ax = plt.gca()
            plt.xlabel(translate('RTOC', 'Time [s]'))
            plt.ylabel(', '.join(signals.keys()))
            plt.grid()
            plt.title(title)
            if len(signals.keys()) == 1:
                ax.legend().set_visible(False)
            else:
                ax.legend().set_visible(True)

            ymean = (ymax+ymin)/2

            ax.xaxis.set_major_formatter(xfmt)
            plt.subplots_adjust(bottom=0.2)
            plt.xticks(rotation=25)
            filetype = 'jpg'
            if type(events)==list:
                for event in events:
                    try:
                        x = dt.datetime.fromtimestamp(event[0])
                        prio = 0
                        if prio == 0:
                            c = 'k'
                        elif prio == 1:
                            c = 'y'
                        else:
                            c = 'r'
                        plt.axvline(x=x, color=c)
                        plt_text(x, ymean, str(event[1]), rotation=90, verticalalignment='center')
                    except Exception as error:
                        print(traceback.format_exc())
                        logging.error('Cannot plot event')

            dir = self.logger.config['global']['documentfolder']
            plt.savefig(dir+'/telegram_export.'+filetype, dpi=dpi)
            # t = self.createSignalInfoStr(signal[2], signal[3])
            if filetype in ['jpg', 'png', 'bmp', 'jpeg']:
                self.send_photo(dir+'/telegram_export.'+filetype, priority=priority, permission=permission, chat_ids=chat_ids)
            else:
                self.send_document(dir+'/telegram_export.'+filetype, priority=priority, permission=permission, chat_ids=chat_ids)
                self.send_message_to_all(text, priority=priority, permission=permission, chat_ids=chat_ids)

    def connect(self):
        idler = Thread(target=self.connectThread)
        idler.start()
        return True

    def connectThread(self):
        try:
            self.updater = Updater(token=self.token)  # bot=self.bot)  #
            self.bot = self.updater.bot
            #self.bot = Bot(self.token)
            self.dispatcher = self.updater.dispatcher

            echo_handler = MessageHandler(Filters.text, self.textHandler)
            self.dispatcher.add_handler(echo_handler)
            start_handler = CommandHandler('start', self.startHandler)
            self.dispatcher.add_handler(start_handler)
            self.dispatcher.add_error_handler(self.error_callback)
            # if self.logger.config['telegram']['inlineMenu']:
            menu_handler = CallbackQueryHandler(self.inlineMenuHandler)
            self.dispatcher.add_handler(menu_handler)
            self.updater.start_polling()
            logging.info('Telegram-Server successfully started!')
            # time.sleep(4)
            #self.sendEvent(self.servername+' wurde gestartet', self.servername, '', 1)
            if WELCOME_MESSAGE:
                for client in self.telegram_clients.keys():
                    self.send_message(
                        int(client), translate('RTOC', '{} was started.').format(self.logger.config['global']['name']))
                    self.menuHandler(int(client), int(client))
            # self.updater.idle()
            return True
        except Exception:
            logging.error('Starting Telegram-Bot failed, maybe wrong telegram-token')
            logging.error(self.logger.config['telegram']['token'])
            # print(traceback.format_exc())
            logging.info(traceback.format_exc())
            return False

    def stop(self):
        logging.info('Telegram-Server stopped!')
        # for chat_id in self.last_messages.keys():
        #     for idx, message_id in enumerate(self.last_messages[chat_id]):
        #         # if idx+1 >= len(self.last_messages[chat_id]):
        #         #     break;
        #         self.bot.delete_message(chat_id, message_id)
        if self.updater:
            self.updater.stop()

    def error_callback(self, bot, update, error):
        try:
            raise error
        except Unauthorized:
            # remove update.message.chat_id from conversation list
            logging.warning('Unauthorized telegram connection')
        except BadRequest:
            # handle malformed requests - read more below!
            logging.warning('The request was malformed')
        except TimedOut:
            # handle slow connection problems
            logging.warning('Connection timed out')
        except NetworkError:
            # handle other connection problems
            logging.warning('Network error occured')
        except ChatMigrated as e:
            # the chat_id of a group has changed, use e.new_chat_id instead
            logging.warning('Chat_ID of group changed')
        except TelegramError:
            # handle all other telegram related errors
            logging.warning('Some other telegram error...')

    def startHandler(self, bot, update):
        self.check_chat_id(update.message.chat_id)
        chat = bot.get_chat(update.message.chat_id)
        bot.send_message(update.message.chat_id, text=translate('RTOC', '*Hello {}!*\nI\'m your {}-bot.\nI will help you to manage the devices you installed. I can also show you the measurement data and notify you at events.').format(chat.first_name, self.logger.config['global']['name']), parse_mode=ParseMode.MARKDOWN)
        self.menuHandler(bot, update.message.chat_id)
#################### Menu helper #################################################

    def build_menu(self, buttons, n_cols, header_buttons=None, footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    def _permissionCheck(self, chat_id):
        if self.bot == None:
            return
        if self.logger.config['telegram']['onlyAdmin'] and self.telegram_clients[str(chat_id)]['permission'] != 'admin':
            #logging.info('Aborted telegram answer, because telegram-option "onlyAdmin" is active.')
            text = translate('RTOC', 'The RTOC bot is in maintenance mode. An administrator must unlock the access.')
            logging.info(text)
            self.bot.send_message(
                chat_id, text=text, disable_notification=False)
            return False

        if self.telegram_clients[str(chat_id)]['permission'] == 'blocked':
            text = translate('RTOC', 'You don\'t have permission for this bot.')
            logging.info(text)
            self.bot.send_message(
                chat_id, text=text, disable_notification=False)
            return False

        return True

    def send_message(self, chat_id, text, parse_mode=ParseMode.MARKDOWN, disable_notification=True, delete=True):
        if self.bot == None:
            return
        if not self._permissionCheck(chat_id):
            return

        try:
            lastMessage = self.bot.send_message(
                chat_id, text=text, disable_notification=True, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            print(traceback.format_exc())
            lastMessage = self.bot.send_message(
                chat_id, text=text, disable_notification=True)

        if delete:
            self._deleteMessageIfOld(chat_id, lastMessage)
        #     self.last_messages[chat_id].append(lastMessage.message_id)
        # if len(self.last_messages[chat_id]) > 3:
        #     message_id = self.last_messages[chat_id].pop(0)
        #     self.bot.delete_message(chat_id, message_id)

    def sendMenuMessage(self, bot, chat_id, buttonlist, text='', description_text='', n_cols=1, backButton=True, inline = False):
        if not self._permissionCheck(chat_id):
            return

        if backButton:
            buttonlist.append(self.BACKBUTTON)

        if description_text != '':
            text = description_text.replace('/n', '/n') + '\n' + text

        if self.logger.config['telegram']['inlineMenu'] or inline:
            self._sendMenuMessage_inline(bot, chat_id, buttonlist, text, n_cols)
        else:
            self._sendMenuMessage_keyboard(bot, chat_id, buttonlist, text, n_cols)


    def _sendMenuMessage_inline(self, bot, chat_id, buttonlist, text, n_cols):
        button_list = [InlineKeyboardButton(s, callback_data=s) for s in buttonlist]
        reply_markup = InlineKeyboardMarkup(self.build_menu(button_list, n_cols=n_cols))

        try:
            lastMessage = self.bot.send_message(
                chat_id, text=text, reply_markup=reply_markup, disable_notification=True, parse_mode=ParseMode.MARKDOWN,)

            self._deleteMessageIfOld(chat_id, lastMessage)
        except Exception:
            try:
                lastMessage = self.bot.send_message(
                    chat_id, text=text, reply_markup=reply_markup, disable_notification=True)

                self._deleteMessageIfOld(chat_id, lastMessage)
            except Exception:
                self._sendMenuMessage_keyboard(nMessages=0)

    def _sendMenuMessage_keyboard(self, bot, chat_id, buttonlist, text, n_cols):
        button_list = [KeyboardButton(s) for s in buttonlist]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=n_cols))

        try:
            lastMessage = self.bot.send_message(
                chat_id, text=text, reply_markup=reply_markup, disable_notification=True, parse_mode=ParseMode.MARKDOWN,)
        except Exception:
            lastMessage = self.bot.send_message(
                chat_id, text=text, reply_markup=reply_markup, disable_notification=True)

        self._deleteMessageIfOld(chat_id, lastMessage)


    def _deleteMessageIfOld(self, chat_id, lastMessage, nMessages=3):
        if chat_id not in self.last_messages.keys():
            self.last_messages[chat_id] = [lastMessage.message_id]
        else:
            self.last_messages[chat_id].append(lastMessage.message_id)
            while len(self.last_messages[chat_id]) > nMessages:
                message_id = self.last_messages[chat_id].pop(0)
                try:
                    self.bot.delete_message(chat_id, message_id)
                except Exception:
                    pass

#################### Menu handler and answers #####################################

    def inlineMenuHandler(self, update, context):
        self.textHandler(self.bot, None, context['callback_query']
                         ['data'], context['callback_query']['message']['chat']['id'])

    def _threadedAns(self, fun, *args, **kwargs):
        if 'chat_id' in kwargs.keys():
            chat_id = kwargs['chat_id']
        else:
            chat_id = args[1]
        if not self.busy:
            self.busy = True
            time.sleep(4)
            t = Thread(target=self._thr, args=(fun, *args, *kwargs,))
            t.start()
        else:
            self.send_message(chat_id, translate('RTOC', 'I\'m busy right now, please give me more time.'))

    def _thr(self, fun, *args, **kwargs):
        fun(*args, *kwargs)
        self.busy = False

    def textHandler(self, bot, update, altStrung=None, alt_chat_id=None):
        if altStrung is None or alt_chat_id is None:
            strung = update.message.text
            chat_id = update.message.chat_id
        else:
            strung = altStrung
            chat_id = alt_chat_id
        self.check_chat_id(chat_id)
        bot.send_chat_action(chat_id=chat_id,
                             action=ChatAction.TYPING)
        if self.telegram_clients[str(chat_id)]['menu'] == "menu":
            self.menuHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == "adjustEventNotification":
            self.adjustEventNotificationHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'plugins':
            self.devicesHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'plugin':
            self.deviceHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'pluginfunctions':
            self.deviceFunctionsHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'pluginsamplerate':
            self.deviceSamplerateHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'pluginparameters':
            self.deviceParametersHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'call' or self.telegram_clients[str(chat_id)]['menu'] == 'callShortcut':
            self.deviceCallHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'signals':
            self.signalsHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'signalSelectRange':
            self.signalsSelectRangeHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == "createEvent":
            self.createEventHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'settings':
            self.settingsHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'settingsGeneral':
            self.settingsGeneralHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'settingsBot':
            self.settingsBotHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'settingsBackup':
            self.settingsBackupHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'resize':
            self.resizeHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == "shortcut":
            self.addShortcutAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'globalSamplerate':
            self.globalSamplerateHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'backupResampling':
            self.backupResamplingHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'automation':
            self.automationHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'globalEvents':
            self.globalEventsHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'globalEvent':
            self.globalEventHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'globalActions':
            self.globalActionsHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'] == 'globalAction':
            self.globalActionHandlerAns(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['menu'].endswith(":signals"):
            self.signalsDeviceSubHandlerAns(bot, chat_id, strung)
        else:
            self.menuHandler(bot, chat_id)


# Main menu


    def menuHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = 'menu'
        self.saveClients()
        # commands = copy.deepcopy(list(self.userActions.keys()))
        commands = []
        perm = self.telegram_clients[str(chat_id)]['permission']
        if perm not in ['read', 'blocked', 'custom']:
            for c in self.logger.userActions.keys():
                if c.startswith('_'):
                    if perm == 'admin':
                        commands += [c]
                else:
                    commands += [c]


        if perm not in ['read', 'blocked']:
            commands += self.createShortcutList(bot, chat_id)
        if perm != 'custom':
            commands += self.menuCommands
        if perm in ['write', 'admin']:
            commands = commands[:-1] + self.writeMenuCommands + [commands[-1]]
        if self.telegram_clients[str(chat_id)]['preview']:
            commands += [translate('RTOC', 'Exit preview')]
        self.sendMenuMessage(bot, chat_id, commands,
                             translate('RTOC', "*Mainmenu*"), '', 1, False)

    def menuHandlerAns(self, bot, chat_id, strung):
        if strung in self.menuCommands:
            idx = self.menuCommands.index(strung)
            if idx == 0:
                self.sendLatest(bot, chat_id)
                self.menuHandler(bot, chat_id)
            elif idx == 1:
                self.signalsHandler(bot, chat_id)
            elif idx == 2:
                self.settingsHandler(bot, chat_id)
        elif strung in list(self.logger.userActions.keys()):
            self.executeUserAction(bot, chat_id, strung)
        elif strung in self.createShortcutList(bot, chat_id):
            self.callShortcut(bot, chat_id, strung)
        elif self.telegram_clients[str(chat_id)]['permission'] in ['write','admin'] and strung in self.writeMenuCommands:
                idx = self.writeMenuCommands.index(strung)
                if idx == 0:
                    self.devicesHandler(bot, chat_id)
                elif idx == 1:
                    self.createEventHandler(bot, chat_id)
                elif idx == 2:
                    self.automationHandler(bot, chat_id)
        elif self.telegram_clients[str(chat_id)]['preview'] and strung == translate('RTOC', 'Exit preview'):
            self.telegram_clients[str(chat_id)]['preview'] = False
            self.telegram_clients[str(chat_id)]['permission'] = 'admin'
        else:
            self.menuHandler(bot, chat_id)

# adjust eventNotification menu
    def adjustEventNotificationHandler(self, bot, chat_id):
        self.adjustEventNotificationCommands = [translate('RTOC', "No notifications"), translate('RTOC', "Only errors"), translate('RTOC', "Warnings"), translate('RTOC', "All events")]
        self.telegram_clients[str(chat_id)]['menu'] = "adjustEventNotification"
        self.saveClients()
        value = self.telegram_clients[str(chat_id)]['eventlevel']
        value = self.adjustEventNotificationCommands[abs(value-3)]
        self.sendMenuMessage(bot, chat_id, self.adjustEventNotificationCommands, translate('RTOC', 'Current level: *{}*\n').format(value), translate('RTOC', 'Choose an notification level.'))

    def adjustEventNotificationHandlerAns(self, bot, chat_id, strung):
        if strung in self.adjustEventNotificationCommands:
            i = self.adjustEventNotificationCommands.index(strung)
            if i <= 3:
                i = abs(i-3)
                self.telegram_clients[str(chat_id)]['eventlevel'] = i
                self.saveClients()
                self.send_message(chat_id=chat_id,
                                  text=translate('RTOC', 'Settings applied'))
        self.settingsHandler(bot, chat_id)

# send latest menu
    def sendLatest(self, bot, chat_id):
        strung = translate('RTOC', "Name    |  Value  | Unit\n------- | ------- | -------\n")
        latest = self.logger.database.getLatest()
        names = list(latest.keys())
        names.sort()
        for name in names:
            sig = latest[name]
            value = sig[1]
            unit = sig[2]
            strung = strung+name+'\t | ' + \
                str(round(value, 2))+"\t | "+str(unit)+"\n"
        if strung == "":
            strung = translate('RTOC', "No signals available")
        self.send_message(chat_id=chat_id, text=strung)

# plugins menu (list of devices)
    def devicesHandler(self, bot, chat_id):
        self.current_plugin[chat_id] = None
        self.telegram_clients[str(chat_id)]['menu'] = "plugins"
        self.saveClients()
        commands = list(self.logger.devicenames)
        commands.sort()
        self.sendMenuMessage(bot, chat_id, commands,
                             translate('RTOC', '*Devices*'))

    def devicesHandlerAns(self, bot, chat_id, strung):
        if strung in self.logger.devicenames.keys():
            self.deviceHandler(bot, chat_id, strung)
        else:
            self.menuHandler(bot, chat_id)

    def deviceHandler(self, bot, chat_id, device):
        self.current_plugin[chat_id] = device
        self.telegram_clients[str(chat_id)]['menu'] = 'plugin'
        self.saveClients()
        if device in self.logger.pluginStatus.keys():
            if self.logger.pluginStatus[device] == True:
                commands = [translate('RTOC', "Stop device")]
                samplestr = '\nSamplerate: '+str(self.logger.getPluginSamplerate(device))+' Hz'
                commands += [translate('RTOC', "Functions"), translate('RTOC', "Parameters"), translate('RTOC', "Change samplerate")]
            elif self.logger.pluginStatus[device] == False:
                commands = [translate('RTOC', "Start device")]
                samplestr = ''
            else:
                commands = [translate('RTOC', "Device-error")]
                samplestr = ''
        else:
            commands = []
            samplestr = translate('RTOC', 'Unknown device')

        self.sendMenuMessage(bot, chat_id, commands, device+samplestr)

    def deviceHandlerAns(self, bot, chat_id, strung):
        if strung == translate('RTOC', "Stop device"):
            self.logger.stopPlugin(self.current_plugin[chat_id])
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        elif strung == translate('RTOC', "Start device"):
            self.logger.startPlugin(self.current_plugin[chat_id])
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        elif strung == translate('RTOC', "Functions"):
            self.deviceFunctionsHandler(bot, chat_id)
        elif strung == translate('RTOC', "Parameters"):
            self.deviceParametersHandler(bot, chat_id)
        elif strung == translate('RTOC', "Change samplerate"):
            self.deviceSamplerateHandler(bot, chat_id)
        elif strung == self.BACKBUTTON:
            self.telegram_clients[str(chat_id)]['menu'] = "plugins"
            self.saveClients()
            self.devicesHandler(bot, chat_id)
        else:
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])

    def deviceSamplerateHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = 'pluginsamplerate'
        self.saveClients()
        name = self.current_plugin[chat_id]
        commands = ['0.1', '0.5', '1', '2', '5', '10']
        samplerate = self.logger.getPluginSamplerate(name)
        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*Change samplerate\nCurrent samplerate: {} Hz').format(samplerate))

    def deviceSamplerateHandlerAns(self, bot, chat_id, strung):
        name = self.current_plugin[chat_id]
        if strung == self.BACKBUTTON:
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        else:
            try:
                samplerate = float(strung)
                self.logger.setPluginSamplerate(name, samplerate)
                self.send_message(chat_id,
                                  translate('RTOC', 'Samplerate was changed'))
                self.deviceHandler(bot, chat_id, name)
            except:
                print(traceback.format_exc())
                self.send_message(chat_id,
                                  translate('RTOC', 'I did not understand your message'))

    def deviceFunctionsHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = 'pluginfunctions'
        self.saveClients()
        name = self.current_plugin[chat_id]
        commands = []
        for fun in self.logger.pluginFunctions.keys():
            hiddenFuncs = ["loadGUI", "updateT", "stream", "plot", "event", "createTCPClient", "close", "cancel", "start", "setSamplerate","setDeviceName",'setPerpetualTimer','setInterval','getDir','telegram_send_message', 'telegram_send_photo', 'telegram_send_document', 'telegram_send_plot']
            hiddenFuncs = [name+'.'+i for i in hiddenFuncs]
            if fun.startswith(name+".") and fun not in hiddenFuncs:
                parStr = ', '.join(self.logger.pluginFunctions[fun][1])
                commands += [fun.replace(name+".", '')+'('+parStr+')']
        commands.sort()
        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*Functions*'))

    def deviceFunctionsHandlerAns(self, bot, chat_id, strung):
        name = self.current_plugin[chat_id]
        if strung == self.BACKBUTTON:
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        else:
            for fun in self.logger.pluginFunctions.keys():
                parStr = ', '.join(self.logger.pluginFunctions[fun][1])
                if fun.replace(name+".", '')+'('+parStr+')' == strung:
                    self.deviceCallHandler(bot, chat_id, strung)
                    return
            self.deviceFunctionsHandler(bot, chat_id)

    def deviceParametersHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = 'pluginparameters'
        self.saveClients()
        name = self.current_plugin[chat_id]
        commands = []
        for fun in self.logger.pluginParameters.keys():
            hiddenParams = ["run", "smallGUI", 'widget', 'samplerate','lockPerpetialTimer', 'logger']
            hiddenParams = [name+'.'+i for i in hiddenParams]
            if fun.startswith(name+".") and fun not in hiddenParams:
                commands += [fun.replace(name+".", '')]
        commands.sort()
        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*Parameters*'))

    def deviceParametersHandlerAns(self, bot, chat_id, strung):
        commands = []
        name = self.current_plugin[chat_id]
        if strung == self.BACKBUTTON:
            self.current_call[chat_id] = None
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        else:
            for fun in self.logger.pluginParameters.keys():
                if fun.replace(name+".", '') == strung:
                    self.deviceCallHandler(bot, chat_id, strung)
                    return
            self.deviceParametersHandler(bot, chat_id)

    def deviceCallHandler(self, bot, chat_id, strung):
        if strung is not None and strung != 'SHORTCUT':
            pre = "call"
            self.current_call[chat_id] = strung
            if strung in self.createShortcutList(bot, chat_id, 1):
                commands = [translate('RTOC', "Remove shortcut")]
            else:
                commands = [translate('RTOC', "Create shortcut")]
        # elif strung == 'SHORTCUT':
        #     pre = "callShortcut"
        #     if self.telegram_clients[str(chat_id)]['permission'] != 'custom':
        #         commands = [translate('RTOC', "Remove shortcut")]
        #     else:
        #         commands = []
        else:
            #self.telegram_clients[str(chat_id)]['menu'] = "shortcut"
            #commands = [translate('RTOC', "Shortcut wie wo?")]
            pre = "callShortcut"
            if self.telegram_clients[str(chat_id)]['permission'] != 'custom':
                commands = [translate('RTOC', "Remove shortcut")]
            else:
                commands = []
        if self.current_call[chat_id].endswith('()') and commands == []:
            func = self.current_call[chat_id][0:self.current_call[chat_id].index('(')]
            self.temp = []
            self._pluginCall_chat_id = chat_id
            ok, ans = self.logger.callPluginFunction(
                self.current_plugin[chat_id], func, *self.temp)
            self._pluginCall_chat_id = None
            if ans is not None:
                self.send_message(chat_id, ans)
            if ok:
                infotext = translate('RTOC', 'Function was executed.')
                # self.send_message(chat_id, translate('RTOC', 'Function was executed.'))
            else:
                infotext = translate('RTOC', 'Error in function.')
                # self.send_message(chat_id, translate('RTOC', 'Error in function.'))
            self.send_message(chat_id, infotext)
            return
        elif self.current_call[chat_id].endswith(')'):
            infotext = translate('RTOC', "Please specify the parameters to be passed to the function. (If necessary)")
            commands += [translate('RTOC', "No parameters")]
            self.telegram_clients[str(chat_id)]['menu'] = pre
            self.saveClients()
        else:
            value = self.logger.getPluginParameter(self.current_plugin[chat_id], "get", [
                                                   self.current_call[chat_id]])
            if value == False:
                devtext = self.current_plugin[chat_id] + \
                '.' + self.current_call[chat_id]
                infotext = translate('RTOC', "*Error*. \nParameter {} not found or device {} not started.").format(devtext, self.current_plugin[chat_id])
                self.sendMenuMessage(bot, chat_id, commands, infotext)
                return

            if type(value) == list:
                if len(value) == 1:
                    value = value[0]
            infotext = translate('RTOC', "Current value: *{}*\nWrite me a new value if you want to change it.").format(value)
            self.telegram_clients[str(chat_id)]['menu'] = pre
            self.saveClients()

            if strung == 'SHORTCUT':
                #self.send_message(chat_id, infotext)
                self.telegram_clients[str(chat_id)]['menu'] = pre
                self.saveClients()
                self.sendMenuMessage(bot, chat_id, commands, infotext)
                #self.menuHandler(bot, chat_id)
                return
        self.sendMenuMessage(bot, chat_id, commands, infotext)

    def deviceCallHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            if self.telegram_clients[str(chat_id)]['menu'] == 'callShortcut':
                self.menuHandler(bot, chat_id)
            else:
                if self.current_call[chat_id].endswith(')'):
                    self.deviceFunctionsHandler(bot, chat_id)
                else:
                    self.deviceParametersHandler(bot, chat_id)
        elif strung == translate('RTOC', "Create shortcut"):
            self.addShortcut(bot, chat_id, strung)
        elif strung == translate('RTOC', "Remove shortcut"):
            self.removeShortcut(bot, chat_id, strung)
        else:
            self.temp = []
            if strung == translate('RTOC', "No parameters"):
                self.temp = []
            else:
                try:
                    if self.current_call[chat_id].endswith(')'):
                        exec('self.temp = ['+strung+']')
                    else:
                        exec('self.temp = '+strung)
                    print(self.temp)
                except Exception:
                    logging.debug(traceback.format_exc())
                    logging.warning(chat_id, text='_'+strung +
                                    " ist not a valid Format._")
                    self.send_message(chat_id, text=translate('RTOC', '_{} is not a valid format._').format(strung))
                    return
            if self.current_call[chat_id].endswith(')'):
                func = self.current_call[chat_id][0:self.current_call[chat_id].index('(')]
                self._pluginCall_chat_id = chat_id
                ok, ans = self.logger.callPluginFunction(
                    self.current_plugin[chat_id], func, *self.temp)
                self._pluginCall_chat_id = None
                self.send_message(chat_id, ans)
                if ok:
                    self.send_message(chat_id, translate('RTOC', 'Function was executed.'))
                else:
                    self.send_message(chat_id, translate('RTOC', 'Error in function.'))
                if self.telegram_clients[str(chat_id)]['menu'] == 'callShortcut':
                    self.menuHandler(bot, chat_id)
                else:
                    self.deviceFunctionsHandler(bot, chat_id)
            else:
                self._pluginCall_chat_id = chat_id
                self.logger.getPluginParameter(
                    self.current_plugin[chat_id], self.current_call[chat_id], self.temp)
                self._pluginCall_chat_id = None
                if self.telegram_clients[str(chat_id)]['menu'] == 'callShortcut':
                    self.menuHandler(bot, chat_id)
                else:
                    self.deviceParametersHandler(bot, chat_id)
            #self.current_call[chat_id] = None
            #self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])

    def get_telegram_client(self, chat_id, entry, alt):
        if entry in self.telegram_clients[str(chat_id)].keys():
            return self.telegram_clients[str(chat_id)][entry]
        else:
            self.telegram_clients[str(chat_id)][entry]=alt
            return alt

    def signalsHandler(self, bot, chat_id, quiet=False):
        self.telegram_clients[str(chat_id)]['menu'] = "signals"
        self.saveClients()
        commands = []
        if chat_id not in self.signals_range.keys():
            xmin_abs = self.logger.database.getGlobalXmin(fast=True)
            xmax = time.time() + 60
            xmin = xmax - 60*60*24
            if xmin_abs > xmin:
                xmin = xmin_abs
            self.signals_range[chat_id] = [xmin-100, xmax+100]
        elif self.signals_range[chat_id] == []:
            xmin_abs = self.logger.database.getGlobalXmin(fast=True)
            xmax = time.time() + 60
            xmin = xmax - 60*60*24
            if xmin_abs > xmin:
                xmin = xmin_abs
            self.signals_range[chat_id] = [xmin-100, xmax+100]
        if chat_id not in self.signals_selected.keys():
            self.signals_selected[chat_id] = []

        availableSignals = self.logger.database.signalNames()
        for signalname in availableSignals:
            sname = '.'.join(signalname)
            if sname in self.signals_selected[chat_id]:
                commands.append('x '+sname)
            elif not self.get_telegram_client(chat_id, 'signalSubmenu', True):
                commands.append(sname)
            elif not signalname[0] in commands and self.get_telegram_client(chat_id, 'signalSubmenu', True):
                commands.append(signalname[0])
        commands.sort()
        commands.insert(0, translate('RTOC', 'Request graph'))
        commands.insert(1, translate('RTOC', 'Select period'))
        if 'Events' in self.signals_selected[chat_id]:
            commands.insert(2, translate('RTOC', 'Hide events'))
        else:
            commands.insert(2, translate('RTOC', 'Show events'))
        if self.signals_selected[chat_id] == ['.'.join(s) for s in availableSignals]:
            commands.append(translate('RTOC', 'Deselect all'))
        else:
            commands.append(translate('RTOC', 'Select all'))
        units = self.logger.database.getUniqueUnits()
        for unit in units:
            commands.append(translate('RTOC', 'Select all with unit "{}"').format(unit))
        if self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            commands.append(translate('RTOC', 'Delete selected signals!'))
            commands.append(translate('RTOC', 'Delete selected events!'))
        commands.append(translate('RTOC', 'Download selected signals!'))
        if self.get_telegram_client(chat_id, 'signalSubmenu', True):
            commands.append(translate('RTOC', 'View: Devices'))
        else:
            commands.append(translate('RTOC', 'View: Signals'))
        if quiet:
            text = translate('RTOC', 'Signals')
        else:
            xmin = self.logger.database.getGlobalXmin(fast=True)
            xmax = self.logger.database.getGlobalXmax(fast=True)
            xmin = dt.datetime.fromtimestamp(xmin).strftime("%d.%m.%Y %H:%M:%S")
            xmax = dt.datetime.fromtimestamp(xmax).strftime("%d.%m.%Y %H:%M:%S")

            xminSel = self.signals_range[chat_id][0]
            xmaxSel = self.signals_range[chat_id][1]
            xminSel = dt.datetime.fromtimestamp(xminSel).strftime("%d.%m.%Y %H:%M:%S")
            xmaxSel = dt.datetime.fromtimestamp(xmaxSel).strftime("%d.%m.%Y %H:%M:%S")
            text = translate('RTOC', '''
*Signals*\n
Here you can get information about signals and I can send you a graph. \n
First select one or more signals and click on "''')+translate('RTOC', 'Request graph')+translate('RTOC', '''".\n
I can also display the events in the plot and delete selected signals or events.\n
Selected period:\n{} - {}\nAvailable period:\n{} - {}''').format(xminSel, xmaxSel, xmin, xmax)
        self.sendMenuMessage(bot, chat_id, commands, text)

    def signalsHandlerAns(self, bot, chat_id, strung):
        chat_id = chat_id
        if chat_id not in self.signals_selected.keys():
            self.signals_selected[chat_id] = []
        if strung == self.BACKBUTTON:
            self.signals_selected[chat_id] = []
            self.signals_range[chat_id] = []
            self.menuHandler(bot, chat_id)
        else:
            units = self.logger.database.getUniqueUnits()
            multiSelectorList = []
            for unit in units:
                multiSelectorList.append(
                    translate('RTOC', 'Select all with unit "{}"').format(unit))

            if strung == translate('RTOC', 'Request graph'):
                plot_signals = []
                dontplot_signals = []
                for sig in self.signals_selected[chat_id]:
                    if sig == 'Events':
                        # pass
                        plot_signals.append(sig)
                    else:
                        names = self.str2signal(sig)
                        sigID = self.logger.database.getSignalID(names[0], names[1])
                        if sigID != -1:
                            plot_signals.append(sig)
                        else:
                            dontplot_signals.append(sig)
                if dontplot_signals != []:
                    self.send_message(chat_id=chat_id,
                                      text=translate('RTOC', '{} can not be plotted.').format(','.join(dontplot_signals)))
                if plot_signals != []:
                    # self.sendSignalPlot(
                    #    bot, chat_id, self.signals_selected[chat_id], *self.signals_range[chat_id])
                    range = list(self.signals_range[chat_id])
                    self.send_message(chat_id=chat_id,
                                      text=translate('RTOC', 'I\'m going to create a graph with {} signals. This may take a while.').format(len(plot_signals)))
                    # t = Thread(target=self.sendSignalPlot, args=(
                    #     bot, chat_id, plot_signals, *range))
                    # t.start()
                    self.sendSignalPlot(bot, chat_id, plot_signals, *range)
                    # self._teleThreads.append(t)
                    # self.signalsHandler(bot, chat_id)
                else:
                    self.send_message(chat_id=chat_id,
                                      text=translate('RTOC', 'No signals selected.'))
            elif strung == translate('RTOC', 'Show events'):
                if 'Events' not in self.signals_selected[chat_id]:
                    self.signals_selected[chat_id].append('Events')
                # else:
                self.send_message(chat_id=chat_id,
                                  text=translate('RTOC', 'Events will be plotted.'))
            elif strung == translate('RTOC', 'Hide events'):
                if 'Events' in self.signals_selected[chat_id]:
                    idx = self.signals_selected[chat_id].index('Events')
                    self.signals_selected[chat_id].pop(idx)
                # else:
                    self.send_message(chat_id=chat_id,
                                      text=translate('RTOC', 'Events will not be plotted.'))
                else:
                    self.send_message(chat_id=chat_id,
                                      text=translate('RTOC', 'You can\'t hide events, they are already hidden!'))
            elif strung.startswith('x '):
                strung = strung.replace('x ', '')
                if strung in self.signals_selected[chat_id]:
                    idx = self.signals_selected[chat_id].index(strung)
                    self.signals_selected[chat_id].pop(idx)
                    self.send_message(chat_id=chat_id,
                                      text=translate('RTOC', 'Signal removed from selection.'))

            elif self.get_telegram_client(chat_id, 'signalSubmenu', True) and strung in self.logger.database.deviceNames():
                self.signalsDeviceSubHandler(bot, chat_id, strung)
                return
            elif strung == translate('RTOC', 'Delete selected signals!'):
                xmin, xmax = self.signals_range[chat_id]
                for sigName in self.signals_selected[chat_id]:
                    if sigName != 'Events':
                        sigID = self.logger.database.getSignalID(*self.str2signal(sigName))
                        if sigID != -1:
                            self.logger.database.removeSignal(sigID, xmin, xmax, True)
                self.signals_selected[chat_id] = []
                self.send_message(chat_id=chat_id,
                                  text=translate('RTOC', 'Selected signals have been deleted!'))
            elif strung == translate('RTOC', 'Delete selected events!'):
                xmin, xmax = self.signals_range[chat_id]
                for sigName in self.signals_selected[chat_id]:
                    if sigName != 'Events':
                        sigID = self.logger.database.getSignalID(*self.str2signal(sigName))
                        if sigID != -1:
                            self.logger.database.removeEvents(sigID, xmin, xmax, True)
                self.send_message(chat_id=chat_id,
                                  text=translate('RTOC', 'Events of selected signals have been deleted!'))
            elif strung == translate('RTOC', 'Select period'):
                self.signalsSelectRangeHandler(bot, chat_id)
                return
            elif strung == translate('RTOC', 'Select all'):
                self.signals_selected[chat_id] == []
                self.signals_selected[chat_id] = [
                    '.'.join(s) for s in self.logger.database.signalNames()]
            elif strung == translate('RTOC', 'Deselect all'):
                self.signals_selected[chat_id] = []
            elif strung in multiSelectorList:
                for unit in units:
                    if '"'+str(unit)+'"' in strung:
                        self.signals_selected[chat_id] == []
                        self.signals_selected[chat_id] = [
                            '.'.join(s) for s in self.logger.database.signalNames(units=[unit])]
                self.signalsHandler(bot, chat_id, True)
                return
            elif strung == translate('RTOC', 'Download selected signals!'):
                bot.send_chat_action(chat_id=chat_id,
                                     action=ChatAction.UPLOAD_DOCUMENT)
                self.send_message(chat_id=chat_id,
                                  text=translate('RTOC', 'I\'m collecting the data now...'))
                sigIDs = [self.logger.database.getSignalID(
                    *self.str2signal(i)) for i in self.signals_selected[chat_id]]
                xmin, xmax = self.signals_range[chat_id]
                dir = self.logger.config['global']['documentfolder']
                self.logger.database.signalsToCSV(
                    sigIDs, dir+'/telegram_export', xmin, xmax, database=True)
                bot.send_document(chat_id=chat_id, document=open(
                    dir+'/telegram_export.csv', 'rb'))
                bot.send_document(chat_id=chat_id, document=open(
                    dir+'/telegram_export.txt', 'rb'))
            elif strung == translate('RTOC', 'View: Devices'):
                self.telegram_clients[str(chat_id)]['signalSubmenu'] = False
                self.saveClients()
            elif strung == translate('RTOC', 'View: Signals'):
                self.telegram_clients[str(chat_id)]['signalSubmenu'] = True
                self.saveClients()
            else:
                self.selectSignal(bot, chat_id, strung)
            self.signalsHandler(bot, chat_id, True)
            return

    def signalsDeviceSubHandler(self, bot, chat_id, device):
        self.telegram_clients[str(chat_id)]['menu'] = device+":signals"
        # self.saveClients()
        commands = []
        availableSignals = self.logger.database.signalNames(devices=[device])
        for signalname in availableSignals:
            sname = '.'.join(signalname)
            if sname not in self.signals_selected[chat_id]:
                commands.append(sname)
        commands = [translate('RTOC', 'All')] +commands
        text = translate('RTOC', 'Signals of {}').format(device)
        commands.sort()
        self.sendMenuMessage(bot, chat_id, commands, text)

    def signalsDeviceSubHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.signalsHandler(bot, chat_id, True)
            return
        elif strung == translate('RTOC', 'All'):
            dev = self.telegram_clients[str(chat_id)]['menu'].split(':')[0]
            availableSignals = self.logger.database.signalNames(devices=[dev])
            for signalname in availableSignals:
                sname = '.'.join(signalname)
                if sname not in self.signals_selected[chat_id] and dev in sname:
                    self.signals_selected[chat_id].append(sname)
            self.send_message(chat_id=chat_id,
                              text=translate('RTOC', 'All signals of {} selected.').format(dev))
        else:
            self.selectSignal(bot, chat_id, strung)
        device = self.telegram_clients[str(chat_id)]['menu'].split(':')[0]
        self.signalsDeviceSubHandler(bot, chat_id, device)

    def str2signal(self, strung):
        a = strung.split('.')
        if len(a)>2:
            # b=['.'.join(a[:-1]),a[-1]]
            b=[a[0],'.'.join(a[1:])]
            return b
        elif len(a) == 2:
            return a

    def selectSignal(self, bot, chat_id, strung):
        a = strung.split('.')
        if len(a)>2:
            self.send_message(chat_id, translate('RTOC', 'Please rename this signal. Signals should not contain "." and ":".'))
            b=['.'.join(a[:-1]),a[-1]]
            self.selectSignal2(bot, chat_id, strung, b)
            b=[a[0],'.'.join(a[1:])]
            self.selectSignal2(bot, chat_id, strung, b)
        elif len(a) == 2:
            self.selectSignal2(bot, chat_id, strung, a)


    def selectSignal2(self, bot, chat_id, strung, a):
        if len(a) == 2:
            if strung not in self.signals_selected[chat_id]:
                sigID = self.logger.database.getSignalID(a[0], a[1])
                if sigID == -1:
                    return
                xmin, xmax, sigLen = self.logger.database.getSignalInfo(sigID)
                if xmin != None:
                    self.signals_selected[chat_id].append(strung)
                    t = self.createPlotToolTip(xmin, xmax, sigLen)
                else:
                    self.signals_selected[chat_id].append(strung)
                    t = translate('RTOC', 'Empty signal')

                evs = self.logger.database.getEvents(sigID)
                if evs == []:
                    evtext = '0'
                else:
                    evtext = str(len(evs))+translate('RTOC', '\nLatest Event:\n')
                    if evs[0][6] == 0:
                        prio = translate('RTOC', 'Information')
                    elif evs[0][6] == 1:
                        prio = translate('RTOC', 'Warning')
                    else:
                        prio = translate('RTOC', 'Error')

                    evtext += prio+': '
                    evtext += evs[0][3]+' am '+ dt.datetime.fromtimestamp(evs[0][4]).strftime("%d.%m.%Y %H:%M:%S")
                self.send_message(chat_id,
                                  translate('RTOC', 'Signal selected:\n{}\nEvents: {}').format(t, evtext), ParseMode.MARKDOWN, True, False)
            return True
        else:
            return False


    def signalsSelectRangeHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = "signalSelectRange"
        # self.saveClients()
        xmin = self.logger.database.getGlobalXmin()
        xmax = self.logger.database.getGlobalXmax()
        xmin = dt.datetime.fromtimestamp(xmin).strftime("%d.%m.%Y %H:%M:%S")
        xmax = dt.datetime.fromtimestamp(xmax).strftime("%d.%m.%Y %H:%M:%S")
        xmin_s, xmax_s = self.signals_range[chat_id]
        xmin_s = dt.datetime.fromtimestamp(xmin_s).strftime("%d.%m.%Y %H:%M:%S")
        xmax_s = dt.datetime.fromtimestamp(xmax_s).strftime("%d.%m.%Y %H:%M:%S")
        text = translate('RTOC', 'Here you can set which range I should display.\nIf you only specify one date, I assume you want to have the dates from that point until now.\nIf you want to specify a time period, separate two times with a "-". You don\'t have to give a time.\nExample: "16.05.19 - 13.06.19 14:33"')
        text += translate('RTOC', '\nSelected period:\n{} - {}\nAvailable period:\n{} - {}\n').format(xmin_s, xmax_s, xmin, xmax)
        commands = [translate('RTOC', 'Last minute'), translate('RTOC', 'Last 10 minutes'), translate('RTOC', 'Last hour'), translate('RTOC', 'Last 24h'), translate('RTOC', 'Last week'), translate('RTOC', 'Last month'), translate('RTOC', 'All')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def signalsSelectRangeHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.signalsHandler(bot, chat_id, True)
        else:
            if strung == translate('RTOC', 'Last minute'):
                xmax = time.time()
                xmin = xmax-60*1
            elif strung == translate('RTOC', 'Last 10 minutes'):
                xmax = time.time()
                xmin = xmax-60*10
            elif strung == translate('RTOC', 'Last hour'):
                xmax = time.time()
                xmin = xmax-60*60*1
            elif strung == translate('RTOC', 'Last 24h'):
                xmax = time.time()
                xmin = xmax-60*60*24
            elif strung == translate('RTOC', 'Last week'):
                xmax = time.time()
                xmin = xmax-60*60*24*7
            elif strung == translate('RTOC', 'Last month'):
                xmax = time.time()
                xmin = xmax-60*60*24*31
            elif strung == translate('RTOC', 'All'):
                xmin = self.logger.database.getGlobalXmin() -100
                # xmax = self.logger.database.getGlobalXmax() +100
                xmax = time.time()+60
            else:
                found, xmin, xmax = _strToTimerange(strung)
                if not found:
                    self.send_message(chat_id=chat_id,
                                      text=translate('RTOC', 'Please send me a period I can understand.'))
                    return
            self.signals_range[chat_id] = [xmin, xmax]
            xmin = dt.datetime.fromtimestamp(xmin).strftime("%d.%m.%Y %H:%M:%S")
            xmax = dt.datetime.fromtimestamp(xmax).strftime("%d.%m.%Y %H:%M:%S")
            text = translate('RTOC', 'Selected period:\n{} - {}').format(xmin, xmax)
            self.send_message(chat_id=chat_id,
                              text=text)
            self.signalsHandler(bot, chat_id, True)

    # dt.datetime.fromtimestamp(time.time()).strftime("%d.%m.%Y %H:%M:%S")

    def createEventHandler(self, bot, chat_id, deviceselect=None, quiet=False):
        self.telegram_clients[str(chat_id)]['menu'] = "createEvent"
        self.saveClients()
        if deviceselect is None or quiet:
            commands = ['.'.join(a) for a in self.logger.database.signalNames()]
            commands.sort()
            if quiet:
                text = deviceselect
            else:
                text = translate('RTOC', '''
*Create event or signal*\n
Send me a message to create an event\n
Write the message bold (*Text*) for an error message and italic (_Text_) for a warning. Normal text has the priority  'Information'\n
You can also send me measured values (e.g. '5 V'). \n
*You can also assign the event/measurement to a signal by selecting a signal from the list or by specifying a signal name ('Device.Signal').\n
                ''')
            self.sendMenuMessage(bot, chat_id, commands, text)
        else:
            self.selectedSignalForEvent = deviceselect
            bot.send_message(chat_id, text=translate('RTOC', "Signal selected: {}.").format(deviceselect))

    def createEventHandlerAns(self, bot, chat_id, strung):
        if strung in ['.'.join(a) for a in self.logger.database.signalNames()]:
            self.createEventHandler(bot, chat_id, strung, False)
        elif len(strung.split('.')) == 2:
            self.createEventHandler(bot, chat_id, strung, False)
        elif strung == self.BACKBUTTON:
            self.selectedSignalForEvent = None
            self.menuHandler(bot, chat_id)
        else:
            if self.selectedSignalForEvent is not None:
                signal = self.selectedSignalForEvent.split('.')
                device = signal[0]
                signal = signal[1]
                #self.selectedSignalForEvent = None
            else:
                device = 'Telegram'
                chat = bot.get_chat(chat_id)
                signal = str(chat.first_name+chat.last_name)
                if signal == '':
                    signal = chat_id

            isValue, value, unit = self.stringToMesswert(strung)
            if isValue:
                self.logger.database.addDataCallback(
                    y=value, unit=[unit], dname=device, snames=[signal])
                # self.send_message(chat_id=chat_id,
                #                   text=translate('RTOC', 'Messwert gesendet.'))
                self.createEventHandler(bot, chat_id, translate('RTOC', 'Value transmitted.'), True)
                return
            else:
                if strung.startswith('*') and strung.endswith('*'):
                    prio = 2
                    strung = strung.replace('*', '')
                elif strung.startswith('_') and strung.endswith('_'):
                    prio = 1
                    strung = strung.replace('_', '')
                else:
                    prio = 0
                self.logger.database.addNewEvent(strung, signal, device, priority=prio)

                # self.send_message(chat_id=chat_id,
                #                   text=translate('RTOC', 'Event gesendet.'))
                self.createEventHandler(bot, chat_id, translate('RTOC', 'Event transmitted.'), True)
                return
            self.menuHandler(bot, chat_id)

    def settingsHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = "settings"
        self.saveClients()
        self.helper[chat_id] = None
        commands = [translate('RTOC', 'Set notification level')]

        if self.telegram_clients[str(chat_id)]['permission'] in ['write','admin']:
            commands += [translate('RTOC', 'General')]
        if self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            commands += [
                translate('RTOC', 'Telegram-Bot'),
                translate('RTOC', 'Backup'),
            ]
        ipadress = urllib.request.urlopen('https://ident.me').read().decode('utf8')
        ipadress = translate('RTOC', '\nIP-Adress: {}').format(ipadress)
        obj_Disk = psutil.disk_usage('/')
        total = str(round(obj_Disk.total / (1024.0 ** 3), 3))
        used = str(round(obj_Disk.used / (1024.0 ** 3), 3))
        free = str(round(obj_Disk.free / (1024.0 ** 3), 3))
        diskspace = translate('RTOC', '\nThere are {}GB of {}GB available.').format(free, total)
        size, maxsize, databaseSize = self.logger.database.getSignalSize()
        if self.logger.config['postgresql']['active']:
            diskspace = diskspace + \
                translate('RTOC', '\nData is beeing saved in PostgreSQL-database')
            diskspace += str(translate('RTOC', '\nDatabase uses...\nTotal: {}\nFor signals: {}\nFor events: {}').format(databaseSize[0],databaseSize[2],databaseSize[3]))
        else:
            diskspace += translate('RTOC', '\nThere are {} of {} available').format(size, maxsize)
        self.sendMenuMessage(bot, chat_id, commands, '*'+self.logger.config['global']['name']+translate('RTOC', '-Settings*')+ipadress+diskspace)

    def settingsHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.menuHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Set notification level'):
            self.adjustEventNotificationHandler(bot, chat_id)
        elif strung == translate('RTOC', 'General') and self.telegram_clients[str(chat_id)]['permission'] in ['write','admin']:
            self.settingsGeneralHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Telegram-Bot') and self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            self.settingsBotHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Backup') and self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            self.settingsBackupHandler(bot, chat_id)
            return
        else:
            self.settingsHandler(bot, chat_id)
            return

    def settingsBotHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = "settingsBot"
        self.saveClients()
        self.helper[chat_id] = None
        commands = []
        if self.logger.config['telegram']['inlineMenu']:
            commands += [translate('RTOC', "Telegram Bot: InlineMenu")]
        else:
            commands += [translate('RTOC', "Telegram Bot: KeyboardMenu")]
        # if self.logger.config['telegram']['active']:
        #     commands += [translate('RTOC', "*Telegram-Bot: On (!)*")]
        # else:
        #     commands += [translate('RTOC', "Telegram-Bot: Off")]
        if self.logger.config['telegram']['onlyAdmin']:
            commands += [translate('RTOC', "OnlyAdmin: On")]
        else:
            commands += [translate('RTOC', "OnlyAdmin: Off")]

        if self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            commands += [
                translate('RTOC', 'Custom-Preview'),
                translate('RTOC', 'Read-Preview'),
                translate('RTOC', 'Write-Preview')
            ]
        commands += [
        translate('RTOC', 'Registered users'),
        ]

        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*Telegram-Bot settings*'))

    def settingsBotHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON and self.helper[chat_id] == 'users':
            self.helper[chat_id] = None
            self.settingsBotHandler(bot, chat_id)
            return
        elif strung == self.BACKBUTTON:
            self.helper[chat_id] = None
            self.settingsHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Registered users'):
            self.helper[chat_id] = 'users'
            text = translate('RTOC', 'Currently registered telegram-users')
            commands = []
            ids = self.telegram_clients.keys()
            for id in ids:
                self.check_chat_id(id)
            for id in ids:
                user = self.telegram_clients[id]
                if self.telegram_clients[id]['permission'] == 'admin':
                    a = translate('RTOC', 'Admin')
                elif self.telegram_clients[id]['permission'] == 'custom':
                    a = translate('RTOC', 'Custom')
                elif self.telegram_clients[id]['permission'] == 'read':
                    a = translate('RTOC', 'Read')
                elif self.telegram_clients[id]['permission'] == 'write':
                    a = translate('RTOC', 'Write')
                else:  # if self.telegram_clients[id]['permission'] == 'blocked':
                    a = translate('RTOC', 'Blocked')
                commands += [user['first_name']+' '+user['last_name']+': '+a]
            self.sendMenuMessage(bot, chat_id, commands, text)
            return
        elif strung == translate('RTOC', 'Custom-Preview') and self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            self.telegram_clients[str(chat_id)]['permission'] = 'custom'
            self.telegram_clients[str(chat_id)]['preview'] = True
            self.telegram_clients[str(chat_id)]['menu'] = 'menu'
            self.logger.config['telegram']['onlyAdmin'] = False
        elif strung == translate('RTOC', 'Write-Preview') and self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            self.telegram_clients[str(chat_id)]['permission'] = 'write'
            self.telegram_clients[str(chat_id)]['preview'] = True
            self.telegram_clients[str(chat_id)]['menu'] = 'menu'
            self.logger.config['telegram']['onlyAdmin'] = False
        elif strung == translate('RTOC', 'Read-Preview') and self.telegram_clients[str(chat_id)]['permission'] == 'admin':
            self.telegram_clients[str(chat_id)]['permission'] = 'read'
            self.telegram_clients[str(chat_id)]['preview'] = True
            self.telegram_clients[str(chat_id)]['menu'] = 'menu'
            self.logger.config['telegram']['onlyAdmin'] = False
        elif self.helper[chat_id] == 'users':
            for id in self.telegram_clients.keys():
                user = self.telegram_clients[id]
                if user['permission'] == 'admin':
                    a = translate('RTOC', 'Admin')
                    next = 'write'
                elif user['permission'] == 'write':
                    a = translate('RTOC', 'Write')#
                    next = 'read'
                elif user['permission'] == 'read':
                    a = translate('RTOC', 'Read')#
                    next = 'custom'
                elif user['permission'] == 'custom':
                    a = translate('RTOC', 'Custom')#
                    next = 'blocked'
                else:  # if self.telegram_clients[id]['permission'] == 'blocked':
                    a = translate('RTOC', 'Blocked')
                    next = 'admin'
                command = user['first_name']+' '+user['last_name']+': '+a
                if command == strung:
                    if str(id) == str(chat_id):
                        self.send_message(chat_id, translate('RTOC', 'You can\'t change your own permissions.'))
                        return
                    if a == translate('RTOC', 'Blocked'):
                        self.send_message(id, translate('RTOC', 'You now have access to this bot.'))
                    self.telegram_clients[id]['permission'] = next
                    self.saveClients()
                    self.settingsBotHandlerAns(bot, chat_id, translate('RTOC', 'Registered users'))
                    return
            return
        elif strung == translate('RTOC', "OnlyAdmin: On"):
            self.logger.config['telegram']['onlyAdmin'] = False
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'OnlyAdmin-Mode', False, True)
            self.settingsBotHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "OnlyAdmin: Off"):
            self.logger.config['telegram']['onlyAdmin'] = True
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'OnlyAdmin-Mode', True, True)
            self.settingsBotHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Telegram Bot: InlineMenu"):
            self.logger.config['telegram']['inlineMenu'] = False
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'InlineMenu', True, True)
            self.settingsBotHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Telegram Bot: KeyboardMenu"):
            self.logger.config['telegram']['inlineMenu'] = True
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'KeyboardMenu', True, True)
            self.settingsBotHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Telegram-Bot: On"):
            ok = self.logger.toggleTelegramBot(False)
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'Telegram-Bot', False, ok)
            self.settingsGeneralHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Telegram-Bot: Off"):
            ok = self.logger.toggleTelegramBot(True)
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'Telegram-Bot', True, ok)
            self.settingsGeneralHandler(bot, chat_id)
            return
        else:
            self.settingsBotHandler(bot, chat_id)
            return

    def sendStartStopMessage(self, chat_id, name, start=True, ok=True):
        if start:
            start = translate('RTOC', '**started**')
        else:
            start = translate('RTOC', '**stopped**')
        if ok:
            text =  translate('RTOC', "{} was {}.").format(name, start)
        else:
            text = translate('RTOC', "{} could not be {}.").format(name, start)

        self.send_message(chat_id, text)

    def settingsBackupHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = "settingsBackup"
        self.saveClients()
        self.helper[chat_id] = None
        commands = []
        if self.logger.config['backup']['active']:
            commands += [
            translate('RTOC', "Backup: On"),
            translate('RTOC', 'Create backup now'),]
            if self.logger.config['backup']['resample'] == 0:
                commands.append(translate('RTOC', 'Auto-resampling: Off'))
            else:
                commands.append(translate('RTOC', 'Auto-resampling: {} Hz').format(self.logger.config['backup']['resample']))
            if self.logger.config['backup']['autoIfFull']:
                commands.append(translate('RTOC', 'Backup, if full: On'))
            else:
                commands.append(translate('RTOC', 'Backup, if full: Off'))
            if self.logger.config['backup']['autoOnClose']:
                commands.append(translate('RTOC', 'Backup on close: On'))
            else:
                commands.append(translate('RTOC', 'Backup on close: Off'))
            if self.logger.config['backup']['loadOnOpen']:
                commands.append(translate('RTOC', 'Load backup on start: On'))
            else:
                commands.append(translate('RTOC', 'Load backup on start: Off'))

            commands.append(translate('RTOC','Backup-Interval: {}s').format(self.logger.config['backup']['intervall']))
        else:
            commands += [translate('RTOC', "Backup: Off")]

        if self.logger.config['postgresql']['active']:
            commands += [
            translate('RTOC', 'Resample database'),
            translate('RTOC', 'Download database'),
            ]
        commands += [
            translate('RTOC', "Delete all data"),
            ]


        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*Backup settings*'))

    def settingsBackupHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON and self.helper[chat_id] != None:
            self.helper[chat_id] = None
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == self.BACKBUTTON:
            self.helper[chat_id] = None
            self.settingsHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', '**Delete all data**'):
            self.logger.clear(True)
            return
        elif strung == translate('RTOC', 'Delete all data'):
            text = translate('RTOC', 'Do you really want to delete all data (signals + events)?')
            commands = [translate('RTOC', '**Delete all data**')]
            self.sendMenuMessage(bot, chat_id, commands, text)
            return
        elif strung == translate('RTOC', 'Create backup now'):
            self.helper[chat_id] = None
            self.logger.database.pushToDatabase()
            self.send_message(chat_id, translate('RTOC', 'Backup was created.'))
            return
        elif strung == translate('RTOC', 'Auto-resampling: {} Hz').format(self.logger.config['backup']['resample']) or strung == translate('RTOC', 'Auto-resampling: Off'):
            self.backupResamplingHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Backup: On"):
            ok = self.logger.config['backup']['active']=False
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'Backup', False, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Backup: Off"):
            ok = self.logger.config['backup']['active']=True
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'Backup', True, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Download database'):
            path = self.logger.config['global']['documentfolder']+'/'
            filepathes = self.logger.database.exportCSV(path+'telegram_export', True)
            for file in filepathes:
                bot.send_document(chat_id=chat_id, document=open(
                    file, 'rb'))

            self.send_message(chat_id, translate('RTOC', 'Database sent.'))
            return
        elif strung == translate('RTOC', 'Resample database'):
            self.sendMenuMessage(bot, chat_id, ['0.01','0.1','0.5','1','5'], translate('RTOC', 'In which samplerate should the data be resampled?'))
            self.helper[chat_id] = 'resample'
            return
        elif self.helper[chat_id] == 'resample':
            try:
                samplerate = float(strung)
            except:
                self.send_message(chat_id, translate('RTOC', 'That wasn\'t a valid input.'))
                return
            self.send_message(chat_id, translate('RTOC', 'Signals are now beeing resampled.\This can take quite a while, depending on the size of the database.'))
            self.logger.database.resampleDatabase(samplerate)
            self.send_message(chat_id, translate('RTOC', 'Signals have been resampled.'))
            self.settingsBackupHandler(bot, chat_id)
            return

        elif strung == translate('RTOC', 'Backup, if full: On'):
            ok = self.logger.config['backup']['autoIfFull']=False
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, translate('RTOC', 'Backup, if full'), False, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Backup, if full: Off'):
            ok = self.logger.config['backup']['autoIfFull']=True
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, translate('RTOC', 'Backup, if full'), True, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Backup on close: On'):
            ok = self.logger.config['backup']['autoOnClose']=False
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, translate('RTOC', 'Backup on close'), False, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Backup on close: Off'):
            ok = self.logger.config['backup']['autoOnClose']=True
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, translate('RTOC', 'Backup on close'), True, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Load backup on start: On'):
            ok = self.logger.config['backup']['loadOnOpen']=False
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, translate('RTOC', 'Load backup on start'), False, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Load backup on start: Off'):
            ok = self.logger.config['backup']['loadOnOpen']=True
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, translate('RTOC', 'Load backup on start'), True, ok)
            self.settingsBackupHandler(bot, chat_id)
            return
        elif strung == translate('RTOC','Backup-Interval: {}s').format(self.logger.config['backup']['intervall']):
            liset = [
                translate('RTOC', 'Off'),
                translate('RTOC', '1x per minute'),
                translate('RTOC', '2x per hour'),
                translate('RTOC', '1x per hour'),
                translate('RTOC', '2x per day'),
                translate('RTOC', '1x per day'),
                translate('RTOC', '2x per week'),
                translate('RTOC', '1x per week'),
            ]
            self.sendMenuMessage(bot, chat_id, liset, translate('RTOC', 'At what intervals should backups be performed? Give me the seconds or select an element from the list.\nBackup interval and local recording duration should match the signal sampling rates.'))
            self.helper[chat_id] = 'resample'
            self.helper[chat_id] = 'Backup-Interval'
            return
        elif self.helper[chat_id] == 'Backup-Interval':
            if strung == translate('RTOC', 'Off'):
                seconds = 0
            elif strung == translate('RTOC', '1x per minute'):
                seconds = 60
            elif strung == translate('RTOC', '2x per hour'):
                seconds = 60*30
            elif strung == translate('RTOC', '1x per hour'):
                seconds = 60*60
            elif strung == translate('RTOC', '2x per day'):
                seconds = 60*60*12
            elif strung == translate('RTOC', '1x per day'):
                seconds = 60*60*24
            elif strung == translate('RTOC', '2x per week'):
                seconds = 60*60*24*3.5
            elif strung == translate('RTOC', '1x per week'):
                seconds = 60*60*24*7
            else:
                try:
                    seconds = float(strung)
                except:
                    self.send_message(chat_id, translate('RTOC', 'That wasn\'t a valid input.'))
                    return
            self.logger.config['backup']['intervall'] = seconds
            self.send_message(chat_id, translate('RTOC', 'Backup-Interval changed.'))
            self.settingsBackupHandler(bot, chat_id)
            return
        else:
            self.settingsBackupHandler(bot, chat_id)
            return

    def settingsGeneralHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = "settingsGeneral"
        self.saveClients()
        self.helper[chat_id] = None
        commands = [
            translate('RTOC', 'Change recording length'),
            translate('RTOC', 'Change global samplerate'),
            ]

        if self.logger.config['websocket']['active']:
            commands += [translate('RTOC', "Websocket-Server: On")]
        else:
            commands += [translate('RTOC', "Websocket-Server: Off")]
        commands += [translate('RTOC', 'Restart server')]

        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*General settings*'))

    def settingsGeneralHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.settingsHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Change recording length'):
            self.telegram_clients[str(chat_id)]['menu'] = 'resize'
            self.saveClients()
            self.resizeHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Change global samplerate'):
            self.globalSamplerateHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Restart server'):
            os.system('sudo reboot')
            time.sleep(5)
            text = translate('RTOC', '**Something didn\'t work.**\nEither I don\'t have the necessary rights, or my home is not a Linux device.')
            self.send_message(chat_id, text)
            return
        elif strung == translate('RTOC', "Websocket-Server: On"):
            ok = self.logger.toggleWebsocketServer(False)
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'Websocket-Server', False, ok)
            self.settingsGeneralHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Websocket-Server: Off"):
            ok = self.logger.toggleWebsocketServer(True)
            self.logger.save_config()
            self.sendStartStopMessage(chat_id, 'Websocket-Server', True, ok)
            self.settingsGeneralHandler(bot, chat_id)
            return
        else:
            self.settingsGeneralHandler(bot, chat_id)
            return

    def backupResamplingHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = 'backupResampling'
        commands = [translate('RTOC', 'Off'), '0.1', '0.5', '1', '2', '5', '10']

        resample = self.logger.config['backup']['resample']
        if resample == 0:
            resample = translate('RTOC', 'Off')
        else:
            resample = str(resample)+' Hz'
        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*Change database resampling*\nCurrent resampling: {}').format(resample))


    def backupResamplingHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.settingsBackupHandler(bot, chat_id)
        else:
            if strung == translate('RTOC', 'Off'):
                self.logger.config['backup']['resample'] = 0
                self.logger.save_config()
                self.send_message(chat_id,
                                  translate('RTOC', 'Resampling has been deactivated'))
                self.settingsBackupHandler(bot, chat_id)
            try:
                samplerate = float(strung)
                self.logger.config['backup']['resample'] = samplerate
                self.logger.save_config()
                self.send_message(chat_id,
                                  translate('RTOC', 'Resampling has been changed'))
                self.settingsBackupHandler(bot, chat_id)
            except:
                print(traceback.format_exc())
                self.send_message(chat_id,
                                  translate('RTOC', 'I did not understand your message'))

    def globalSamplerateHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = 'globalSamplerate'
        self.saveClients()
        commands = ['0.1', '0.5', '1', '2', '5', '10']
        self.sendMenuMessage(bot, chat_id, commands, translate('RTOC', '*Change samplerate for all running devices*'))

    def globalSamplerateHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.settingsGeneralHandler(bot, chat_id)
        else:
            try:
                samplerate = float(strung)
                self.logger.setAllSamplerates(samplerate)
                self.send_message(chat_id,
                                  translate('RTOC', 'Samplerate has been changed'))
                self.settingsGeneralHandler(bot, chat_id)
            except:
                print(traceback.format_exc())
                self.send_message(chat_id,
                                  translate('RTOC', 'I did not understand your message'))

    def resizeHandler(self, bot, chat_id):
        commands = ['1', '10', '100', '1000', '10000',
                    '1000000', '250000', '500000', '750000', '1000000']
        plotLen = self.logger.config['global']['recordLength']
        size, maxsize, databaseSize = self.logger.database.getSignalSize()
        if self.logger.config['postgresql']['active']:
            text = translate('RTOC', "The recording length does not affect the recording lenght of the database, which is unlimited. \nCurrent recording length: {}").format(plotLen)
        else:
            text = translate('RTOC', "Current recording length: {}").format(self.logger.config['global']['recordLength'])
        self.sendMenuMessage(bot, chat_id, commands, text)

    def resizeHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.settingsGeneralHandler(bot, chat_id)
        else:
            try:
                value = int(strung)
            except ValueError:
                logging.debug(traceback.format_exc())
                logging.error('Not a valid user input')
                value = None
            if value:
                self.send_message(chat_id=chat_id, text=translate('RTOC', 'Recording length has been changed'))
                self.logger.database.resizeSignals(value)
                self.logger.save_config()
                self.settingsGeneralHandler(bot, chat_id)
            else:
                self.send_message(chat_id=chat_id,
                                  text=translate('RTOC', 'Invalid input'))
                self.settingsGeneralHandler(bot, chat_id)

    def sendSignalPlot(self, bot, chat_id, signalnames, xmin_plot, xmax_plot):
        if plt is None:
            self.send_message(chat_id=chat_id,
                              text=translate('RTOC', '**I couldn\'t create a plot.**\nYou need to install "matplotlib" and "tkinker" on my server.**'))
            return
        # bio = BytesIO()
        # bio.name = 'image.png'
        # bot.send_chat_action(chat_id=chat_id,
        #                      action=ChatAction.UPLOAD_PHOTO)
        if type(signalnames) == str:
            signalnames = [signalnames]
        if 'Events' in signalnames:
            plotEvents = True
            signalnames.pop(signalnames.index('Events'))
        else:
            plotEvents = False
        plt.gcf().clear()
        units = []

        xmin = time.time()
        xmax = 0
        ymin = 0
        ymax = 0
        maxLen = 0

        for idx, signalname in enumerate(signalnames):
            # a = signalname.split('.')
            a = self.str2signal(signalname)
            signal = self.logger.database.getSignal_byName(
                a[0], a[1], xmin=xmin_plot, xmax=xmax_plot, database=True, maxN=1000)
            # bot.send_chat_action(chat_id=chat_id,
            #                      action=ChatAction.UPLOAD_PHOTO)
            if signal is not None:
                if len(signal[2])>0:
                    if min(signal[2]) < xmin:
                        xmin = min(signal[2])
                    if max(signal[2]) > xmax:
                        xmax = max(signal[2])
                    if max(signal[3]) > ymax:
                        ymax = max(signal[3])
                    if min(signal[3]) > ymin:
                        ymin = min(signal[3])
                    if len(signal[2]) > maxLen:
                        maxLen = len(signal[2])
                    if signal[4] not in units:
                        units.append(signal[4])
                    if len(signal[2]) != len(signal[3]):
                        diff = abs(len(signal[3]) - len(signal[2]))
                        if len(signal[2]) > len(signal[3]):
                            signal[3] += [signal[3][-1]] * diff
                        else:
                            signal[2] += [signal[2][-1]] * diff
                    try:
                        #dates = [dt.datetime.fromtimestamp(float(ts)) for ts in list(signal[2])]
                        dates = []
                        for ts in list(signal[2]):
                            if type(ts) == list:
                                print(ts)
                            dates.append(dt.datetime.fromtimestamp(float(ts)))
                        if abs(signal[2][0]-signal[2][-1]) > 5*60:
                            xfmt = mdates.DateFormatter(translate('RTOC', '%d.%m %H:%M'))
                        else:
                            xfmt = mdates.DateFormatter(translate('RTOC', '%d.%m %H:%M:%S'))
                        plt.plot(dates, list(signal[3]), label=signalname + '['+signal[4]+']')  # ,'-x')
                    except Exception as error:
                        print(error)
                        print(traceback.format_exc())
                        logging.error(traceback.format_exc())

            proc = (idx+1)/len(signalnames)*100
            self.send_message(chat_id=chat_id,
                              text=translate('RTOC', 'Plot completed at {}%.').format(round(proc)))

        ax = plt.gca()
        plt.xlabel(translate('RTOC', 'Time [s]'))
        plt.ylabel(', '.join(units))
        plt.grid()
        plt.title(', '.join(signalnames))
        if len(signalnames) == 1:
            ax.legend().set_visible(False)
        else:
            ax.legend().set_visible(True)

        ax.xaxis.set_major_formatter(xfmt)
        plt.subplots_adjust(bottom=0.2)
        plt.xticks(rotation=25)
        filetype = 'jpg'
        ymean = (ymax+ymin)/2
        if plotEvents:
            try:
                for evID in self.logger.database.events().keys():
                    event = self.logger.database.events()[evID]
                    if event[4] > xmin_plot and event[4] < xmax_plot:
                        # [DEVICE_ID,SIGNAL_ID,EVENT_ID,TEXT,TIME,VALUE,PRIORITY]
                        prio = event[6]
                        text = event[3]
                        x = dt.datetime.fromtimestamp(event[4])
                        name = self.logger.database.getEventName(evID)
                        if name != None:
                            name = '.'.join(name)+': '
                        else:
                            name = ''

                        if prio == 0:
                            c = 'k'
                        elif prio == 1:
                            c = 'y'
                        else:
                            c = 'r'
                        plt.axvline(x=x, color=c)
                        plt_text(x, ymean, name+text, rotation=90, verticalalignment='center')
            except Exception as error:
                print(traceback.format_exc())
                logging.error('Cannot plot events')
        dir = self.logger.config['global']['documentfolder']
        plt.savefig(dir+'/telegram_export.'+filetype, dpi=DPI)
        # t = self.createSignalInfoStr(signal[2], signal[3])
        t = self.createPlotToolTip(xmin, xmax, maxLen)
        bot.send_chat_action(chat_id=chat_id,
                             action=ChatAction.UPLOAD_PHOTO)
        if filetype in ['jpg', 'png', 'bmp', 'jpeg']:
            bot.send_photo(chat_id=chat_id, photo=open(
                dir+'/telegram_export.'+filetype, 'rb'), caption=t, timeout=1000)
        else:
            bot.send_document(chat_id=chat_id, document=open(
                dir+'/telegram_export.'+filetype, 'rb'), timeout=1000)
            self.send_message(chat_id, t, ParseMode.MARKDOWN, True, False)
        #self.devicesHandler(bot, chat_id)

    def createPlotToolTip(self, xmin, xmax, sigLen):
        maxduration = round(self.calcMaxDuration(xmin, xmax, sigLen))
        duration = round(xmax-xmin)
        try:
            if self.logger.config['postgresql']['active']:
                line1 = translate('RTOC', 'Duration: {}').format(dt.timedelta(seconds=duration))
                line2 = str(sigLen) + translate('RTOC', ' values')
            else:
                line1 = str(dt.timedelta(seconds=duration)) + '/ ~ ' + \
                    str(dt.timedelta(seconds=maxduration))
                line2 = str(sigLen)+"/"+str(self.logger.config['global']['recordLength'])

            if duration != 0:
                line3 = str(round(sigLen/(duration), 2)) + ' Hz'
            else:
                line3 = translate('RTOC', 'Empty signal')
            return line1+"\n"+line2 + "\n" + line3
        except Exception:
            print(traceback.format_exc())
            logging.debug(traceback.format_exc())
            logging.error('Formatting signal information failed.')
            return translate('RTOC', '')

    def createSignalInfoStr(self, x, y):
        maxduration = round(self.calcMaxDuration(x[0], x[-1], len(x)))
        duration = round(x[-1]-x[0])
        try:
            if self.logger.config['postgresql']['active']:
                line1 = translate('RTOC', 'Duration: {}').format(dt.timedelta(seconds=duration))
                line2 = str(len(list(x))) + translate('RTOC', ' values')
            else:
                line1 = str(dt.timedelta(seconds=duration)) + '/ ~ ' + \
                    str(dt.timedelta(seconds=maxduration))
                line2 = str(
                    len(list(x)))+"/"+str(self.logger.config['global']['recordLength'])

            count = 20
            if len(x) <= count:
                count = len(x)
            if count > 1:
                meaner = list(x)[-count:]
                diff = 0
                for idx, m in enumerate(meaner[:-1]):
                    diff += meaner[idx+1]-m
                if diff != 0:
                    line3 = str(round((len(meaner)-1)/diff, 2))+" Hz"
                else:
                    line3 = "? Hz"
            else:
                line3 = "? Hz"
            return line1+"\n"+line2 + "\n" + line3
        except Exception:
            print(traceback.format_exc())
            logging.debug(traceback.format_exc())
            logging.error('Formatting signal information failed.')
            return translate('RTOC', 'I could not create any info for this signal.')

    def checkShortcutButton(self):
        pass

    def createShortcutList(self, bot, chat_id, idx=0):
        liste = list(self.telegram_clients[str(chat_id)]['shortcuts'][idx])
        if idx == 1:
            for idx, name in enumerate(liste):
                liste[idx] = name.split('.')[1]
        return liste

    def addShortcut(self, bot, chat_id, strung):
        device = self.current_plugin[chat_id]
        call = self.current_call[chat_id]
        call = device+'.'+call
        if call not in self.telegram_clients[str(
                chat_id)]['shortcuts']:

            self.telegram_clients[str(chat_id)]['menu'] = "shortcut"
            self.saveClients()
            self.sendMenuMessage(bot, chat_id, [self.current_call[chat_id]], translate('RTOC', 'Please enter a name for this shortcut.'))
        else:
            self.send_message(chat_id, translate('RTOC', 'For this function/this parameter already exists a shortcut!'))
            self.deviceCallHandler(bot, chat_id, self.current_call[chat_id])

    def addShortcutAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.deviceCallHandler(bot, chat_id, self.current_call[chat_id])
        elif strung in self.menuCommands:
            self.send_message(chat_id, translate('RTOC', 'You cannot name the shortcut like an entry in the main menu.'))
        elif strung in self.createShortcutList(bot, chat_id):
            self.send_message(chat_id, translate('RTOC', 'Please choose a different name. This one is already in use.'))
        else:
            chat_id = chat_id
            device = self.current_plugin[chat_id]
            call = self.current_call[chat_id]
            call = device+'.'+call
            # logging.debug(call)
            if call not in self.telegram_clients[str(chat_id)]['shortcuts']:
                self.telegram_clients[str(chat_id)]['shortcuts'][0].append(strung)
                self.telegram_clients[str(chat_id)]['shortcuts'][1].append(call)
                self.send_message(chat_id, translate('RTOC', 'Shortcut has been created'))
                self.saveClients()
            else:
                self.send_message(chat_id, translate('RTOC', 'For this function/this parameter already exists a shortcut!'))
            self.deviceCallHandler(bot, chat_id, None)
            if self.current_call[chat_id] is not None:
                if self.current_call[chat_id].endswith(')'):
                    self.deviceFunctionsHandler(bot, chat_id)
                else:
                    self.deviceParametersHandler(bot, chat_id)
            else:
                self.deviceCallHandler(bot, chat_id, None)

    def removeShortcut(self, bot, chat_id, strung):
        if self.current_call[chat_id] is not None:
            strung = self.current_plugin[chat_id]+'.'+self.current_call[chat_id]
            print(strung)
            if strung in self.telegram_clients[str(chat_id)]['shortcuts'][1]:
                idx = self.telegram_clients[str(
                    chat_id)]['shortcuts'][1].index(strung)
                self.telegram_clients[str(
                    chat_id)]['shortcuts'][1].pop(idx)
                self.telegram_clients[str(
                    chat_id)]['shortcuts'][0].pop(idx)
                self.current_call[chat_id] = None
                self.menuHandler(bot, chat_id)
                self.saveClients()
            else:
                self.send_message(chat_id, translate('RTOC', 'Sorry, I couldn\'t find that shortcut!'))
                self.menuHandler(bot, chat_id)
        else:
            self.send_message(chat_id, translate('RTOC', 'You reached the end of the universe'))
            self.menuHandler(bot, chat_id)

    def callShortcut(self, bot, chat_id, strung):
        if strung in self.telegram_clients[str(chat_id)]['shortcuts'][0]:
            idx = self.telegram_clients[str(
                chat_id)]['shortcuts'][0].index(strung)
            call = self.telegram_clients[str(
                chat_id)]['shortcuts'][1][idx].split('.')
            self.current_plugin[chat_id] = call[0]
            self.current_call[chat_id] = call[1]
            self.deviceCallHandler(bot, chat_id, 'SHORTCUT')
        else:
            self.send_message(chat_id, translate('RTOC', 'Sorry, I couldn\'t find that shortcut!'))

    def calcMaxDuration(self, xmin, xmax, sigLen):
        if sigLen > 2:
            dt = xmax-xmin
            maxlen = self.logger.config['global']['recordLength']
            return dt/sigLen*maxlen
        else:
            return -1

    def stringToMesswert(self, strung):
        if len(strung.split(' ')) > 2:
            return False, None, None
        else:
            if len(strung.split(' ')) == 2:
                text = strung.split(' ')
                value = text[0]
                unit = text[1]
            elif len(strung.split(' ')) == 1:
                value = strung
                unit = ''
            try:
                value = float(value)
                return True, value, unit
            except Exception:
                return False, None, None

    def automationHandler(self, bot, chat_id, quiet=False):
        self.telegram_clients[str(chat_id)]['menu'] = "automation"
        self.saveClients()
        commands = []
        if self.logger.config['global']['globalActionsActivated']:
            commands += [translate('RTOC', "Global actions: On")]
        else:
            commands += [translate('RTOC', "Global actions: Off")]
        if self.logger.config['global']['globalEventsActivated']:
            commands += [translate('RTOC', "Global events: On")]
        else:
            commands += [translate('RTOC', "Global events: Off")]
        commands += [translate('RTOC', "Edit actions")]
        commands += [translate('RTOC', "Edit events")]
        text = '# '+translate('RTOC', "Automation")
        if not quiet:
            text += translate('RTOC', '''
\n
Here you can view and edit global events and actions.\n
Global events are created when a specified condition is met. For example "Temperature at sensor X exceeds 80°C". If the condition is fulfilled, the specified event is created. (Event=[message, priority, ID])
\n
Global actions are executed when an event with a specified ID has been created. The action consists of a piece of Python code.
        ''')
        self.sendMenuMessage(bot, chat_id, commands, text)

    def automationHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.menuHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Global actions: On"):
            self.logger.config['global']['globalActionsActivated'] = False
        elif strung == translate('RTOC', "Global actions: Off"):
            self.logger.config['global']['globalActionsActivated'] = True
        elif strung == translate('RTOC', "Global events: On"):
            self.logger.config['global']['globalEventsActivated'] = False
        elif strung == translate('RTOC', "Global events: Off"):
            self.logger.config['global']['globalEventsActivated'] = True
        elif strung == translate('RTOC', "Edit actions"):
            ok = self.globalActionsHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', "Edit events"):
            ok = self.globalEventsHandler(bot, chat_id)
            return
        self.automationHandler(bot, chat_id, quiet=True)

        # self.send_message(chat_id, text)

    def globalEventsHandler(self, bot, chat_id):
        if chat_id not in self.signals_selected.keys():
            self.signals_selected[chat_id] = []
        self.helper[chat_id] = None
        self.telegram_clients[str(chat_id)]['menu'] = "globalEvents"
        self.saveClients()
        commands = []
        text = translate('RTOC', 'Global events')
        commands += self.logger.printGlobalEvents()
        commands += [translate('RTOC', 'Create new global event')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalEventsHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.signals_selected[chat_id] = []
            self.automationHandler(bot, chat_id)
            return
        elif strung in self.logger.printGlobalEvents():
            self.signals_selected[chat_id] = strung
            self.globalEventHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Create new global event'):
            text = translate('RTOC','Give the new event a name')
            self.send_message(chat_id, text)
        elif strung != '':
            self.logger.addGlobalEvent(strung)
            self.logger.saveGlobalEvents()
            self.globalEventsHandler(bot, chat_id)

    def globalEventHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = "globalEvent"
        self.saveClients()
        if type(self.signals_selected[chat_id])!= str:
            self.menuHandler(bot, chat_id)
            return
        name = self.signals_selected[chat_id].split(': ')
        event = self.logger.globalEvents[name[0]]
        # {'cond', 'text', 'priority', 'return', 'id', 'rising, 'sname', 'dname'}
        if event['priority'] == 0:
            prio = translate('RTOC', 'Information')
        elif event['priority'] == 1:
            prio = translate('RTOC', 'Warning')
        else:
            prio = translate('RTOC', 'Error')
        commands = []
        text = translate('RTOC', '# Event: {}\nText: {}\nPriority: {}\nID: {}\nSignal: {}.{}\nCondition: {}').format(name[0], event['text'], prio, event['id'], event['dname'], event['sname'], event['cond'])
        if event['active']:
            commands += [translate('RTOC', 'Active')]
        else:
            commands += [translate('RTOC', 'Inactive')]
        commands += [translate('RTOC', 'Edit condition')]
        commands += [translate('RTOC', 'Set assigned signal')]
        if event['trigger']=='rising':
            commands += [translate('RTOC', 'Trigger: Rising')]
        elif event['trigger']=='falling':
            commands += [translate('RTOC', 'Trigger: Falling')]
        elif event['trigger']=='both':
            commands += [translate('RTOC', 'Trigger: Rising+Falling')]
        elif event['trigger']=='true':
            commands += [translate('RTOC', 'Trigger: True')]
        elif event['trigger']=='false':
            commands += [translate('RTOC', 'Trigger: False')]
        commands += [translate('RTOC', 'Change event-ID')]
        commands += [translate('RTOC', 'Change text')]
        commands += [translate('RTOC', 'Priority: ')+prio]
        commands += [translate('RTOC', 'Delete event')]
        commands += [translate('RTOC', 'Test event')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalEventHandlerAns(self, bot, chat_id, strung):
        if type(self.signals_selected[chat_id])!= str:
            self.menuHandler(bot, chat_id)
            return
        name = self.signals_selected[chat_id].split(': ')
        event = self.logger.globalEvents[name[0]]
        # {'cond', 'text', 'priority', 'return', 'id', 'rising, 'sname', 'dname'}

        if strung == self.BACKBUTTON and self.helper[chat_id] == None:
            self.helper[chat_id] = None
            self.globalEventsHandler(bot, chat_id)
            return
        elif strung == self.BACKBUTTON:
            self.helper[chat_id] = None
            self.globalEventHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Active'):
            self.logger.globalEvents[name[0]]['active'] = False
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Inactive'):
            self.logger.globalEvents[name[0]]['active'] = True
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Edit condition'):
            self.helper[chat_id] = 'changeCondition'
            signals = self.logger.database.signalNames()
            text = translate('RTOC', 'Available signals:\n')
            text += '\n'.join(['.'.join(i)+'.latest' for i in signals])
            # self.send_message(chat_id, text)
            self.sendMenuMessage(bot, chat_id, [], text)
            return
        elif strung == translate('RTOC', 'Set assigned signal'):
            self.helper[chat_id] = 'selectSignal'
            commands = ['.'.join(a) for a in self.logger.database.signalNames()]
            commands.sort()
            text = translate('RTOC', 'Select a signal or enter a new signalname.')
            self.sendMenuMessage(bot, chat_id, commands, text)
            return
        elif strung == translate('RTOC', 'Trigger: Falling'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['trigger'] = 'rising'
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Trigger: Rising'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['trigger'] = 'both'
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Trigger: Rising+Falling'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['trigger'] = 'false'
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Trigger: False'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['trigger'] = 'true'
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Trigger: True'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['trigger'] = 'falling'
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Change event-ID'):
            text = translate('RTOC', 'Enter an EventID now.')
            self.send_message(chat_id, text)
            self.helper[chat_id] = 'editEventID'
            return
        elif strung == translate('RTOC', 'Change text'):
            text = translate('RTOC', 'Enter the event text now.')
            self.send_message(chat_id, text)
            self.helper[chat_id] = 'editText'
            return
        elif strung == translate('RTOC', 'Priority: ')+translate('RTOC', 'Information'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['priority'] = 1
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Priority: ')+translate('RTOC', 'Warning'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['priority'] = 2
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Priority: ')+translate('RTOC', 'Error'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['priority'] = 0
            self.logger.saveGlobalEvents()
        elif strung == translate('RTOC', 'Delete event'):
            self.helper[chat_id] = None
            self.logger.removeGlobalEvent(name[0])
            self.logger.saveGlobalEvents()
            self.globalEventsHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Test event'):
            self.helper[chat_id] = None
            ok, text = self.logger.triggerGlobalEvent(name[0])
            if text is None:
                text = translate('RTOC', 'You reached the end of the universe')
            self.send_message(chat_id, text)
        elif self.helper[chat_id] == 'editText':
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['text'] = strung
            self.logger.saveGlobalEvents()
        elif self.helper[chat_id] == 'editEventID':
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['id'] = strung
            self.logger.saveGlobalEvents()
        elif self.helper[chat_id] == 'changeCondition':
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['cond'] = strung
            self.logger.saveGlobalEvents()
        elif self.helper[chat_id] == 'selectSignal':
            self.helper[chat_id] = None
            if strung in ['.'.join(a) for a in self.logger.database.signalNames()]:
                ok = True
            elif len(strung.split('.')) == 2:
                ok = True
            else:
                ok = False
            if ok:
                signame = strung.split('.')
                self.logger.globalEvents[name[0]]['sname'] = signame[1]
                self.logger.globalEvents[name[0]]['dname'] = signame[0]

        # self.helper[chat_id] = None
        self.globalEventHandler(bot, chat_id)

    def globalActionsHandler(self, bot, chat_id):
        if chat_id not in self.signals_selected.keys():
            self.signals_selected[chat_id] = []
        self.helper[chat_id] = None
        self.telegram_clients[str(chat_id)]['menu'] = "globalActions"
        self.saveClients()
        commands = []
        text = translate('RTOC', 'Global actions')
        commands += self.logger.printGlobalActions()

        commands += [translate('RTOC', 'Create new global action')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalActionsHandlerAns(self, bot, chat_id, strung):
        if strung == self.BACKBUTTON:
            self.signals_selected[chat_id] = []
            self.automationHandler(bot, chat_id)
            return
        elif strung in self.logger.printGlobalActions():
            self.signals_selected[chat_id] = strung
            self.globalActionHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Create new global action'):
            text = translate('RTOC', 'Give the new action a name')
            self.send_message(chat_id, text)
        elif strung != '':
            self.logger.addGlobalAction(strung)
            self.logger.saveGlobalActions()
            self.globalActionsHandler(bot, chat_id)

    def globalActionHandler(self, bot, chat_id):
        self.telegram_clients[str(chat_id)]['menu'] = "globalAction"
        self.saveClients()
        name = self.signals_selected[chat_id].split(':')
        action = self.logger.globalActions[name[0]]
        # {'listenID', 'script', 'parameters'}
        commands = []
        text = translate('RTOC', '# Action: {}\nEvent-ListenIDs: {}\nScript: \n{}\n').format(name[0], ', '.join(action['listenID']), action['script'])
        if action['active']:
            commands += [translate('RTOC', 'Active')]
        else:
            commands += [translate('RTOC', 'Inactive')]
        commands += [translate('RTOC', 'Edit code')]
        commands += [translate('RTOC', 'Select eventID')]
        commands += [translate('RTOC', 'Delete action')]
        commands += [translate('RTOC', 'Test action')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalActionHandlerAns(self, bot, chat_id, strung):
        if type(self.signals_selected[chat_id]) != str:
            self.globalActionsHandler(bot, chat_id)
            return
        name = self.signals_selected[chat_id].split(':')
        action = self.logger.globalActions[name[0]]

        if strung == self.BACKBUTTON and self.helper[chat_id] == None:
            self.helper[chat_id] = None
            self.globalActionsHandler(bot, chat_id)
            return
        elif strung == self.BACKBUTTON:
            self.helper[chat_id] = None
            self.globalActionHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Active'):
            self.helper[chat_id] = None
            self.logger.globalActions[name[0]]['active'] = False
            self.logger.saveGlobalActions()
        elif strung == translate('RTOC', 'Inactive'):
            self.helper[chat_id] = None
            self.logger.globalActions[name[0]]['active'] = True
            self.logger.saveGlobalActions()
        elif strung == translate('RTOC', 'Edit code'):
            self.helper[chat_id] = 'changeCode'
            plugins = self.logger.getPluginDict()
            signals = self.logger.database.signalNames()
            text = translate('RTOC', 'Available signals:\n')
            text += '\n'.join(['.'.join(i)+'.latest' for i in signals])
            self.send_message(chat_id, text)
            for name in plugins.keys():
                if plugins[name]['status'] is True:
                    text = translate('RTOC', '{} parameters:\n').format(name)
                    text += '\n'.join([i[0] for i in plugins[name]['parameters']])
                    text += translate('RTOC', '\n\n{} functions:\n').format(name)
                    text += '\n'.join([i+'()' for i in plugins[name]['functions']])
                    self.send_message(chat_id, text)
            self.sendMenuMessage(bot, chat_id, [], translate('RTOC', 'Edit code'))
            return
        elif strung == translate('RTOC', 'Select eventID'):
            self.helper[chat_id] = 'selectIDs'
            events = self.logger.database.getUniqueEvents(False)
            commands = []
            for key in events.keys():
                commands.append(key)
            text = translate('RTOC', 'Select events to call this action.')
            self.sendMenuMessage(bot, chat_id, commands, text)
            return
        elif strung == translate('RTOC', 'Delete action'):
            self.helper[chat_id] = None
            self.logger.removeGlobalAction(name[0])
            self.logger.saveGlobalActions()
            self.globalActionsHandler(bot, chat_id)
            return
        elif strung == translate('RTOC', 'Test action'):
            self.helper[chat_id] = None
            ok, text = self.logger.triggerGlobalAction(name[0])
            if text is None:
                text = translate('RTOC', 'You reached the end of the universe')
            self.send_message(chat_id, text)
            return
        elif self.helper[chat_id] == 'selectIDs':
            self.helper[chat_id] = None
            self.logger.globalActions[name[0]]['listenID'] = [strung]
            self.logger.saveGlobalEvents()
        elif self.helper[chat_id] == 'changeCode':
            self.helper[chat_id] = None
            self.logger.globalActions[name[0]]['script'] = strung
            self.logger.saveGlobalEvents()

        # self.helper[chat_id] =
        self.globalActionHandler(bot, chat_id)

    def executeUserAction(self, bot, chat_id, strung):
        ok, ans = self.logger.executeUserAction(strung)
        if ok and len(ans) == 2:
            try:
                text = translate('RTOC', 'Action has been executed')
                if ans[0] == 'picture':
                    bot.send_photo(chat_id=chat_id, photo=open(ans[1], 'rb'))
                elif ans[0] == 'document':
                    bot.send_document(chat_id=chat_id, document=open(
                        ans[1], 'rb'))
                elif ans[0] == 'text':
                    self.send_message(chat_id, ans[1])
            except:
                text = translate('RTOC', 'Action is incorrect')
                self.send_message(chat_id, text)
        else:
            text = translate('RTOC', 'Action is incorrect')
            self.send_message(chat_id, text)

def _strToTimestamp(datetimestr):
    while datetimestr.endswith(' '):
        datetimestr = datetimestr[0:-1]
    while datetimestr.startswith(' '):
        datetimestr = datetimestr[1:]
    formats = []
    dates = ['%d.%m.%Y', '%d.%m', '%m.%Y', '%d.%m.%y', '%m/%d', '%m/%d/%y',
             '%m/%d/%Y', '%m-%d-%y', '%m-%d-%Y', '%d. %B %Y', '%B %Y']
    times = ['%H:%M:%S', '%H:%M']

    for d in dates:
        formats += [d]
        for t in times:
            formats += [t]
            formats += [d+' '+t]
            formats += [t+' '+d]

    for format in formats:
        try:
            ts = dt.datetime.strptime(datetimestr, format)
            if 'y' not in format.lower():
                ts = ts.replace(year=2019)
            ts = ts.timestamp()

            return True, ts
            break
        except Exception:
            pass
    return False, None


def _strToTimerange(rangestr):
    if len(rangestr.split('-')) == 2:
        times = rangestr.split('-')
        foundXmin, xmin = _strToTimestamp(times[0])
        foundXmax, xmax = _strToTimestamp(times[1])
        if not foundXmin or not foundXmax:
            return False, None, None
        else:
            return True, xmin, xmax
    else:
        xmax = time.time()
        foundXmin, xmin = _strToTimestamp(rangestr)
        if not foundXmin:
            return False, None, None
        else:
            return True, xmin, xmax
