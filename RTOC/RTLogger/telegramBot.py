import time
from threading import Thread
# from io import BytesIO
import urllib.request

import json
from telegram.ext import MessageHandler, CommandHandler, CallbackQueryHandler, Filters, Updater
from telegram import KeyboardButton, ReplyKeyboardMarkup, ChatAction, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
from ..lib import general_lib as lib
import os
import traceback
import psutil
import datetime as dt
import copy

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

# Bot.answer_callback_query(callback_query_id, text=None, show_alert=False, url=None, cache_time=None, timeout=None, **kwargs) für Teilen
# Bot.delete_message(chat_id, message_id, timeout=None, **kwargs)

try:
    from PyQt5.QtCore import QCoreApplication

    translate = QCoreApplication.translate
except ImportError:
    def translate(id, text):
        return text

__imports__ = ['python-telegram-bot']

BACKBUTTON = translate('telegram', '<-- Zurück')
DPI = 300
WELCOME_MESSAGE = False


class telegramBot():
    """
    This class handles the communication with telegram-clients.
    """

    def __init__(self, logger):
        self.logger = logger

        self.mode = {}
        self.selectedSignalForEvent = None
        self.servername = self.logger.config['global']['name']
        self.token = self.logger.config['telegram']['token']
        self.updater = None
        self.current_plugin = {}
        self.current_call = {}
        self.last_messages = {}
        self.signals_selected = {}
        self.signals_range = {}
        self.helper = {}
        self._teleThreads = []
        self.busy = False
        self.menuCommands = [translate('telegram', 'Event-Benachrichtigung festlegen'), translate(
            'telegram', 'Letzte Messwerte'), translate('telegram', 'Signale'), translate('telegram', 'Geräte'), translate('telegram', 'Event/Signal erzeugen'), translate('telegram', 'Automatisierung'), translate('telegram', 'Einstellungen')]

        userpath = self.logger.config['global']['documentfolder']
        if os.path.exists(userpath+"/telegramActions.json"):
            try:
                with open(userpath+"/telegramActions.json", encoding="UTF-8") as jsonfile:
                    self.userActions = json.load(jsonfile, encoding="UTF-8")
            except:
                # print(traceback.print_exc())
                self.userActions = {}
                logging.error('Error in Telegram-UserActions-JSON-File')

    def setToken(self, token):
        self.token = token
        self.logger.config['telegram']['token'] = token

    def check_chat_id(self, chat_id):
        if chat_id is not None:
            if str(chat_id) not in list(self.logger.config['telegram']['chat_ids'].keys()):
                chat = self.bot.get_chat(chat_id)
                text = str(chat.first_name+' '+chat.last_name)+translate('telegram', ' hat sich zum ersten Mal mit ') + \
                    str(self.logger.config['global']['name'])+translate('telegram', ' verbunden.')
                self.send_message_to_all(text)
                logging.info('TELEGRAM BOT: New client connected with ID: '+str(chat_id))
                self.logger.config['telegram']['chat_ids'][str(
                    chat_id)] = [self.logger.config['telegram']['eventlevel'], [[], []]]
                self.logger.save_config()

            if chat_id not in self.mode.keys():
                self.mode[chat_id] = 'menu'
                self.current_plugin[chat_id] = None
                self.current_call[chat_id] = None

    def sendEvent(self, message, devicename, signalname, priority):
        ptext = ['_Information_', '*Warnung*', '*_Fehler_*'][priority]
        message = ptext+' von ' + devicename+'.'+signalname+':\n'+message
        for id in self.logger.config['telegram']['chat_ids'].keys():
            if priority >= self.logger.config['telegram']['chat_ids'][id][0]:
                try:
                    self.bot.send_message(chat_id=int(id), text=message,
                                          parse_mode=ParseMode.MARKDOWN)
                except Exception:
                    self.bot.send_message(chat_id=int(id), text=message)

    def send_message_to_all(self, message):
        for id in self.logger.config['telegram']['chat_ids'].keys():
            try:
                self.bot.send_message(chat_id=int(id), text=message,
                                      parse_mode=ParseMode.MARKDOWN)
            except Exception:
                self.bot.send_message(chat_id=int(id), text=message)

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
            if self.logger.config['telegram']['inlineMenu']:
                menu_handler = CallbackQueryHandler(self.inlineMenuHandler)
                self.dispatcher.add_handler(menu_handler)
            self.updater.start_polling()
            logging.info('Telegram-Server successfully started!')
            # time.sleep(4)
            #self.sendEvent(self.servername+' wurde gestartet', self.servername, '', 1)
            if WELCOME_MESSAGE:
                for client in self.logger.config['telegram']['chat_ids'].keys():
                    self.send_message(
                        int(client), self.logger.config['global']['name'] + translate('telegram', ' wurde gestartet.'))
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
        bot.send_message(update.message.chat_id, text=translate(
            'telegram', "*Hallo ")+chat.first_name+translate('telegram', "!*\nIch bin dein ")+self.logger.config['global']['name']+translate('telegram', '-Bot.\nIch helfe dir dabei die Geräte zu verwalten, die du bei mir angelegt hast. Außerdem kann ich dir die Messdaten zeigen und dich bei Events benachrichtigen.'), parse_mode=ParseMode.MARKDOWN)
        self.menuHandler(bot, update.message.chat_id)
#################### Menu helper #################################################

    def build_menu(self, buttons, n_cols, header_buttons=None, footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    def send_message(self, chat_id, text, parse_mode=ParseMode.MARKDOWN, disable_notification=True, delete=True):
        try:
            lastMessage = self.bot.send_message(
                chat_id, text=text, disable_notification=True, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            print(traceback.format_exc())
            lastMessage = self.bot.send_message(
                chat_id, text=text, disable_notification=True)
        if chat_id not in self.last_messages.keys():
            self.last_messages[chat_id] = [lastMessage.message_id]

        if delete:
            self.last_messages[chat_id].append(lastMessage.message_id)
        if len(self.last_messages[chat_id]) > 3:
            message_id = self.last_messages[chat_id].pop(0)
            self.bot.delete_message(chat_id, message_id)

    def sendMenuMessage(self, bot, chat_id, buttonlist, text='', description_text='', n_cols=1, backButton=True):

        if backButton:
            buttonlist.append(BACKBUTTON)
        if not self.logger.config['telegram']['inlineMenu']:
            button_list = [KeyboardButton(s) for s in buttonlist]
        else:
            button_list = [InlineKeyboardButton(s, callback_data=s) for s in buttonlist]
        if not self.logger.config['telegram']['inlineMenu']:
            reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=n_cols))
        else:
            reply_markup = InlineKeyboardMarkup(self.build_menu(button_list, n_cols=n_cols))
        if description_text != '':
            text = description_text.replace('/n', '/n') + '\n' + text

        if not self.logger.config['telegram']['inlineMenu']:
            try:
                lastMessage = self.bot.send_message(
                    chat_id, text=text, reply_markup=reply_markup, disable_notification=True, parse_mode=ParseMode.MARKDOWN,)
            except Exception:
                lastMessage = self.bot.send_message(
                    chat_id, text=text, reply_markup=reply_markup, disable_notification=True)
            if chat_id not in self.last_messages.keys():
                self.last_messages[chat_id] = [lastMessage.message_id]
            else:
                self.last_messages[chat_id].append(lastMessage.message_id)
                if len(self.last_messages[chat_id]) > 3:
                    message_id = self.last_messages[chat_id].pop(0)
                    try:
                        self.bot.delete_message(chat_id, message_id)
                    except Exception:
                        pass
        else:
            # self.bot.send_message(
            #     chat_id, text=text, reply_markup=reply_markup)
            try:
                lastMessage = self.bot.send_message(
                    chat_id, text=text, reply_markup=reply_markup, disable_notification=True, parse_mode=ParseMode.MARKDOWN,)
            except Exception:
                lastMessage = self.bot.send_message(
                    chat_id, text=text, reply_markup=reply_markup, disable_notification=True)
            if chat_id not in self.last_messages.keys():
                self.last_messages[chat_id] = [lastMessage.message_id]
            else:
                self.last_messages[chat_id].append(lastMessage.message_id)
                if len(self.last_messages[chat_id]) > 0:
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
            self.send_message(chat_id, translate(
                'telegram', 'Ich bin gerade beschäftigt, bitte lasse mir mehr Zeit.'))

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
        if self.mode[chat_id] == "menu":
            self.menuHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == "adjustEventNotification":
            self.adjustEventNotificationHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'plugins':
            self.devicesHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'plugin':
            self.deviceHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'pluginfunctions':
            self.deviceFunctionsHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'pluginsamplerate':
            self.deviceSamplerateHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'pluginparameters':
            self.deviceParametersHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'call' or self.mode[chat_id] == 'callShortcut':
            self.deviceCallHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'signals':
            self.signalsHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'signalSelectRange':
            self.signalsSelectRangeHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == "createEvent":
            self.createEventHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'settings':
            self.settingsHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'resize':
            self.resizeHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == "shortcut":
            self.addShortcutAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'globalSamplerate':
            self.globalSamplerateHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'automation':
            self.automationHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'globalEvents':
            self.globalEventsHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'globalEvent':
            self.globalEventHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'globalActions':
            self.globalActionsHandlerAns(bot, chat_id, strung)
        elif self.mode[chat_id] == 'globalAction':
            self.globalActionHandlerAns(bot, chat_id, strung)
        else:
            self.menuHandler(bot, chat_id)


# Main menu


    def menuHandler(self, bot, chat_id):
        self.mode[chat_id] = 'menu'
        commands = copy.deepcopy(list(self.userActions.keys()))
        commands += self.createShortcutList(bot, chat_id)
        commands += self.menuCommands
        self.sendMenuMessage(bot, chat_id, commands,
                             translate('telegram', "*Hauptmenü*"), '', 1, False)

    def menuHandlerAns(self, bot, chat_id, strung):
        if strung in self.menuCommands:
            idx = self.menuCommands.index(strung)
            if idx == 0:
                self.adjustEventNotificationHandler(bot, chat_id)
            elif idx == 1:
                self.sendLatest(bot, chat_id)
                self.menuHandler(bot, chat_id)
            elif idx == 2:
                self.signalsHandler(bot, chat_id)
            elif idx == 3:
                self.devicesHandler(bot, chat_id)
            elif idx == 4:
                self.createEventHandler(bot, chat_id)
            elif idx == 5:
                self.automationHandler(bot, chat_id)
            elif idx == 6:
                self.settingsHandler(bot, chat_id)
        elif strung in list(self.userActions.keys()):
            self.executeUserAction(bot, chat_id, strung)
        elif strung in self.createShortcutList(bot, chat_id):
            self.callShortcut(bot, chat_id, strung)
        else:
            self.menuHandler(bot, chat_id)

# adjust eventNotification menu
    adjustEventNotificationCommands = [translate('telegram', "Keine Benachrichtigung"), translate(
        'telegram', "Nur Fehlermeldungen"), translate('telegram', "Warnungen"), translate('telegram', "Alle Benachrichtigungen")]

    def adjustEventNotificationHandler(self, bot, chat_id):
        self.mode[chat_id] = "adjustEventNotification"
        value = self.logger.config['telegram']['chat_ids'][str(chat_id)][0]
        value = self.adjustEventNotificationCommands[abs(value-3)]
        self.sendMenuMessage(bot, chat_id, self.adjustEventNotificationCommands, translate(
            'telegram', '*Derzeitige Stufe: *')+value+'\n', translate('telegram', 'Wähle eine Benachrichtigungsstufe aus.'))

    def adjustEventNotificationHandlerAns(self, bot, chat_id, strung):
        if strung in self.adjustEventNotificationCommands:
            i = self.adjustEventNotificationCommands.index(strung)
            if i <= 3:
                i = abs(i-3)
                self.logger.config['telegram']['chat_ids'][str(chat_id)][0] = i
                self.logger.save_config()
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Einstellung angepasst'))
        self.menuHandler(bot, chat_id)

# send latest menu
    def sendLatest(self, bot, chat_id):
        strung = translate(
            'telegram', "Name\t | Wert\t | Einheit\n -\t | -\t | -\t | -\n")
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
            strung = translate('telegram', "Keine Messwerte vorhanden")
        self.send_message(chat_id=chat_id, text=strung)

# plugins menu (list of devices)
    def devicesHandler(self, bot, chat_id):
        self.current_plugin[chat_id] = None
        self.mode[chat_id] = "plugins"
        commands = list(self.logger.devicenames)
        commands.sort()
        self.sendMenuMessage(bot, chat_id, commands,
                             translate('telegram', '*Geräte*'))

    def devicesHandlerAns(self, bot, chat_id, strung):
        if strung in self.logger.devicenames.keys():
            self.deviceHandler(bot, chat_id, strung)
        else:
            self.menuHandler(bot, chat_id)

    def deviceHandler(self, bot, chat_id, device):
        self.current_plugin[chat_id] = device
        self.mode[chat_id] = 'plugin'
        if self.logger.pluginStatus[device] == True:
            commands = [translate('telegram', "Gerät beenden")]
            samplestr = '\nSamplerate: '+str(self.logger.getPluginSamplerate(device))+' Hz'
            commands += [translate('telegram', "Funktionen"), translate('telegram',
                                                                        "Parameter"), translate('telegram', "Samplerate ändern")]
        elif self.logger.pluginStatus[device] == False:
            commands = [translate('telegram', "Gerät starten")]
            samplestr = ''
        else:
            commands = [translate('telegram', "Gerätefehler")]
            samplestr = ''

        self.sendMenuMessage(bot, chat_id, commands, device+samplestr)

    def deviceHandlerAns(self, bot, chat_id, strung):
        if strung == translate('telegram', "Gerät beenden"):
            self.logger.stopPlugin(self.current_plugin[chat_id])
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        elif strung == translate('telegram', "Gerät starten"):
            self.logger.startPlugin(self.current_plugin[chat_id])
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        elif strung == translate('telegram', "Funktionen"):
            self.deviceFunctionsHandler(bot, chat_id)
        elif strung == translate('telegram', "Parameter"):
            self.deviceParametersHandler(bot, chat_id)
        elif strung == translate('telegram', "Samplerate ändern"):
            self.deviceSamplerateHandler(bot, chat_id)
        elif strung == BACKBUTTON:
            self.mode[chat_id] = "plugins"
            self.devicesHandler(bot, chat_id)
        else:
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])

    def deviceSamplerateHandler(self, bot, chat_id):
        self.mode[chat_id] = 'pluginsamplerate'
        name = self.current_plugin[chat_id]
        commands = ['0.1', '0.5', '1', '2', '5', '10']
        samplestr = str(self.logger.getPluginSamplerate(name))+' Hz'
        self.sendMenuMessage(bot, chat_id, commands, translate(
            'telegram', '*Samplerate ändern*\nDerzeitige Samplerate: '+samplestr))

    def deviceSamplerateHandlerAns(self, bot, chat_id, strung):
        name = self.current_plugin[chat_id]
        if strung == BACKBUTTON:
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        else:
            try:
                samplerate = float(strung)
                self.logger.setPluginSamplerate(name, samplerate)
                self.send_message(chat_id,
                                  translate('telegram', 'Samplerate wurde geändert'))
                self.deviceHandler(bot, chat_id, name)
            except:
                print(traceback.format_exc())
                self.send_message(chat_id,
                                  translate('telegram', 'Ich habe deine Nachricht nicht verstanden'))

    def deviceFunctionsHandler(self, bot, chat_id):
        self.mode[chat_id] = 'pluginfunctions'
        name = self.current_plugin[chat_id]
        commands = []
        for fun in self.logger.pluginFunctions.keys():
            if fun.startswith(name+".") and fun not in [name+".close", name+".loadGUI", name+".createTCPClient", name+".sendTCP", name+".plot", name+".setDeviceName", name+".event", name+".stream"]:
                commands += [fun.replace(name+".", '')+'()']
        commands.sort()
        self.sendMenuMessage(bot, chat_id, commands, translate('telegram', '*Funktionen*'))

    def deviceFunctionsHandlerAns(self, bot, chat_id, strung):
        name = self.current_plugin[chat_id]
        if strung == BACKBUTTON:
            self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])
        else:
            for fun in self.logger.pluginFunctions.keys():
                if fun.replace(name+".", '')+'()' == strung:
                    self.deviceCallHandler(bot, chat_id, strung)
                    return
            self.deviceFunctionsHandler(bot, chat_id)

    def deviceParametersHandler(self, bot, chat_id):
        self.mode[chat_id] = 'pluginparameters'
        name = self.current_plugin[chat_id]
        commands = []
        for fun in self.logger.pluginParameters.keys():
            if fun.startswith(name+".") and fun not in [name+".deviceName", name+".close", name+".run", name+".smallGUI", name+".sock", name+".widget"]:
                commands += [fun.replace(name+".", '')]
        commands.sort()
        self.sendMenuMessage(bot, chat_id, commands, translate('telegram', '*Parameter*'))

    def deviceParametersHandlerAns(self, bot, chat_id, strung):
        commands = []
        name = self.current_plugin[chat_id]
        if strung == BACKBUTTON:
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
                commands = [translate('telegram', "Shortcut entfernen")]
            else:
                commands = [translate('telegram', "Shortcut erstellen")]
        elif strung == 'SHORTCUT':
            pre = "callShortcut"
            commands = [translate('telegram', "Shortcut entfernen")]
        else:
            #self.mode[chat_id] = "shortcut"
            #commands = [translate('telegram', "Shortcut wie wo?")]
            pre = "callShortcut"
            commands = [translate('telegram', "Shortcut entfernen")]
        if "()" in self.current_call[chat_id]:
            infotext = translate(
                'telegram', "Bitte gib Parameter an, die der Funktion übergeben werden sollen. (Falls benötigt)")
            commands += [translate('telegram', "Keine Parameter")]
            self.mode[chat_id] = pre
        else:
            value = self.logger.getPluginParameter(self.current_plugin[chat_id], "get", [
                                                   self.current_call[chat_id]])
            if value != False:
                infotext = translate(
                    'telegram', "Derzeitiger Wert: *")+str(value)+translate('telegram', "*\nSchreib mir einen neuen Wert, wenn du diesen ändern willst.")
                self.mode[chat_id] = pre
            else:
                devtext = self.current_plugin[chat_id] + \
                    '.' + self.current_call[chat_id]
                infotext = translate(
                    'telegram', "*Fehler*. \nParameter ")+devtext.replace('_', '_')+translate('telegram', " nicht gefunden bzw. Gerät ")+self.current_plugin[chat_id].replace('_', '_')+translate('telegram', " nicht gestartet.")
                if strung == 'SHORTCUT':
                    self.send_message(chat_id, infotext)
                    self.menuHandler(bot, chat_id)
                    return
        self.sendMenuMessage(bot, chat_id, commands, infotext)

    def deviceCallHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            if self.mode[chat_id] == 'callShortcut':
                self.menuHandler(bot, chat_id)
            else:
                if "()" in self.current_call[chat_id]:
                    self.deviceFunctionsHandler(bot, chat_id)
                else:
                    self.deviceParametersHandler(bot, chat_id)
        elif strung == translate('telegram', "Shortcut erstellen"):
            self.addShortcut(bot, chat_id, strung)
        elif strung == translate('telegram', "Shortcut entfernen"):
            self.removeShortcut(bot, chat_id, strung)
        else:
            self.temp = []
            if strung == translate('telegram', "Keine Parameter"):
                self.temp = []
            else:
                try:
                    exec('self.temp = '+strung+'')
                except Exception:
                    logging.debug(traceback.format_exc())
                    logging.warning(chat_id, text='_'+strung +
                                    " ist kein gültiges Format._")
                    self.send_message(chat_id, text='_'+strung +
                                      " ist kein gültiges Format._")
                    return
            if "()" in self.current_call[chat_id]:
                self.logger.callPluginFunction(
                    self.current_plugin[chat_id], self.current_call[chat_id], *self.temp)
                if self.mode[chat_id] == 'callShortcut':
                    self.menuHandler(bot, chat_id)
                else:
                    self.deviceFunctionsHandler(bot, chat_id)
            else:
                self.logger.getPluginParameter(
                    self.current_plugin[chat_id], self.current_call[chat_id], self.temp)
                if self.mode[chat_id] == 'callShortcut':
                    self.menuHandler(bot, chat_id)
                else:
                    self.deviceParametersHandler(bot, chat_id)
            #self.current_call[chat_id] = None
            #self.deviceHandler(bot, chat_id, self.current_plugin[chat_id])

    def signalsHandler(self, bot, chat_id, quiet=False):
        self.mode[chat_id] = "signals"
        commands = []
        if chat_id not in self.signals_range.keys():
            xmin_abs = self.logger.database.getGlobalXmin(fast=True)
            xmax = self.logger.database.getGlobalXmax(fast=True)
            xmin = xmax - 60*60*24
            if xmin_abs > xmin:
                xmin = xmin_abs
            self.signals_range[chat_id] = [xmin-100, xmax+100]
        elif self.signals_range[chat_id] == []:
            xmin_abs = self.logger.database.getGlobalXmin(fast=True)
            xmax = self.logger.database.getGlobalXmax(fast=True)
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
            else:
                commands.append(sname)
        commands.sort()
        commands.insert(0, translate('telegram', 'Graph anfordern'))
        commands.insert(1, translate('telegram', 'Zeitraum wählen'))
        if 'Events' in self.signals_selected[chat_id]:
            commands.insert(2, translate('telegram', 'Events ausblenden'))
        else:
            commands.insert(2, translate('telegram', 'Events anzeigen'))
        if self.signals_selected[chat_id] == ['.'.join(s) for s in availableSignals]:
            commands.append(translate('telegram', 'Alle abwählen'))
        else:
            commands.append(translate('telegram', 'Alle auswählen'))
        units = self.logger.database.getUniqueUnits()
        for unit in units:
            commands.append(translate('telegram', 'Alle mit Einheit "') +
                            str(unit)+translate('telegram', '" auswählen'))
        commands.append(translate('telegram', 'Ausgewähle Signale löschen!'))
        commands.append(translate('telegram', 'Ausgewählte Events löschen!'))
        commands.append(translate('telegram', 'Ausgewählte Signale herunterladen'))
        if quiet:
            text = translate('telegram', 'Signale')
        else:
            xmin = self.logger.database.getGlobalXmin(fast=True)
            xmax = self.logger.database.getGlobalXmax(fast=True)
            xmin = dt.datetime.fromtimestamp(xmin).strftime("%d.%m.%Y %H:%M:%S")
            xmax = dt.datetime.fromtimestamp(xmax).strftime("%d.%m.%Y %H:%M:%S")

            xminSel = self.signals_range[chat_id][0]
            xmaxSel = self.signals_range[chat_id][1]
            xminSel = dt.datetime.fromtimestamp(xminSel).strftime("%d.%m.%Y %H:%M:%S")
            xmaxSel = dt.datetime.fromtimestamp(xmaxSel).strftime("%d.%m.%Y %H:%M:%S")
            text = translate('telegram', '''
            *Signale*\n
            Hier bekommst du Infos über Signale und ich kann dir einen Graphen schicken. \n
            Wähle dazu zuerst ein oder mehrere Signale aus und klicke auf "''')+translate('telegram', 'Graph anfordern')+'".\n'+translate('telegram', '''
            Ich kann auch die Events im Plot darstellen und ausgewählte Signale oder Events löschen.\n
            Ausgewählter Zeitraum:\n''')+xminSel+' - '+xmaxSel+'.'+translate('telegram', '\nVerfügbarer Zeitraum:\n')+xmin+' - '+xmax
        self.sendMenuMessage(bot, chat_id, commands, text)

    # tooltip sofort anzeigen, for neuen Tooltip x min und x max, längen
    # text braucht mean(y)
    def signalsHandlerAns(self, bot, chat_id, strung):
        chat_id = chat_id
        if chat_id not in self.signals_selected.keys():
            self.signals_selected[chat_id] = []
        if strung == BACKBUTTON:
            self.signals_selected[chat_id] = []
            self.signals_range[chat_id] = []
            self.menuHandler(bot, chat_id)
        else:
            a = strung.split('.')
            units = self.logger.database.getUniqueUnits()
            multiSelectorList = []
            for unit in units:
                multiSelectorList.append(
                    translate('telegram', 'Alle mit Einheit "')+str(unit)+translate('telegram', '" auswählen'))

            if strung == translate('telegram', 'Graph anfordern'):
                plot_signals = []
                dontplot_signals = []
                for sig in self.signals_selected[chat_id]:
                    if sig == 'Events':
                        pass
                    else:
                        names = sig.split('.')
                        sigID = self.logger.database.getSignalID(names[0], names[1])
                        if sigID != -1:
                            plot_signals.append(sig)
                        else:
                            dontplot_signals.append(sig)
                if dontplot_signals != []:
                    self.send_message(chat_id=chat_id,
                                      text=','.join(dontplot_signals)+translate('telegram', ' können nicht dargestellt werden.'))
                if plot_signals != []:
                    # self.sendSignalPlot(
                    #    bot, chat_id, self.signals_selected[chat_id], *self.signals_range[chat_id])
                    range = list(self.signals_range[chat_id])
                    self.send_message(chat_id=chat_id,
                                      text=translate('telegram', 'Ich erzeuge jetzt einen Graphen mit ')+str(len(plot_signals))+translate('telegram', ' Signalen.\nDas kann eine Weile dauern'))
                    t = Thread(target=self.sendSignalPlot, args=(
                        bot, chat_id, plot_signals, *range))
                    t.start()
                    # self._teleThreads.append(t)
                    # self.signalsHandler(bot, chat_id)
                else:
                    self.send_message(chat_id=chat_id,
                                      text=translate('telegram', 'Keine Signale ausgewählt.'))
            elif strung == translate('telegram', 'Events anzeigen'):
                if 'Events' not in self.signals_selected[chat_id]:
                    self.signals_selected[chat_id].append('Events')
                # else:
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Events werden dargestellt.'))
            elif strung == translate('telegram', 'Events ausblenden'):
                if 'Events' in self.signals_selected[chat_id]:
                    idx = self.signals_selected[chat_id].index('Events')
                    self.signals_selected[chat_id].pop(idx)
                # else:
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Events werden nicht dargestellt.'))
            elif strung.startswith('x '):
                strung = strung.replace('x ', '')
                if strung in self.signals_selected[chat_id]:
                    idx = self.signals_selected[chat_id].index(strung)
                    self.signals_selected[chat_id].pop(idx)
                    self.send_message(chat_id=chat_id,
                                      text=translate('telegram', 'Signal aus Auswahl entfernt.'))
            elif len(a) == 2:
                if strung not in self.signals_selected[chat_id]:
                    sigID = self.logger.database.getSignalID(a[0], a[1])
                    xmin, xmax, sigLen = self.logger.database.getSignalInfo(sigID)
                    if xmin != None:
                        self.signals_selected[chat_id].append(strung)
                        t = self.createPlotToolTip(xmin, xmax, sigLen)
                    else:
                        self.signals_selected[chat_id].append(strung)
                        t = 'Leeres Signal'
                    self.send_message(chat_id,
                                      translate('telegram', 'Signal ausgewählt:\n')+t, ParseMode.MARKDOWN, True, False)
            elif strung == translate('telegram', 'Ausgewähle Signale löschen!'):
                xmin, xmax = self.signals_range[chat_id]
                for sigName in self.signals_selected[chat_id]:
                    if sigName != 'Events':
                        sigID = self.logger.database.getSignalID(*sigName.split('.'))
                        if sigID != -1:
                            self.logger.database.removeSignal(sigID, xmin, xmax, True)
                self.signals_selected[chat_id] = []
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Ausgewählte Signale wurden gelöscht'))
            elif strung == translate('telegram', 'Ausgewählte Events löschen!'):
                xmin, xmax = self.signals_range[chat_id]
                for sigName in self.signals_selected[chat_id]:
                    if sigName != 'Events':
                        sigID = self.logger.database.getSignalID(*sigName.split('.'))
                        if sigID != -1:
                            self.logger.database.removeEvents(sigID, xmin, xmax, True)
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Events der ausgewählten Signale wurden gelöscht'))
            elif strung == translate('telegram', 'Zeitraum wählen'):
                self.signalsSelectRangeHandler(bot, chat_id)
                return
            elif strung == translate('telegram', 'Alle auswählen'):
                self.signals_selected[chat_id] == []
                self.signals_selected[chat_id] = [
                    '.'.join(s) for s in self.logger.database.signalNames()]
            elif strung == translate('telegram', 'Alle abwählen'):
                self.signals_selected[chat_id] = []
            elif strung in multiSelectorList:
                for unit in units:
                    if '"'+str(unit)+'"' in strung:
                        self.signals_selected[chat_id] == []
                        self.signals_selected[chat_id] = [
                            '.'.join(s) for s in self.logger.database.signalNames(units=[unit])]
                self.signalsHandler(bot, chat_id, True)
                return
            elif strung == translate('telegram', 'Ausgewählte Signale herunterladen'):
                bot.send_chat_action(chat_id=chat_id,
                                     action=ChatAction.UPLOAD_DOCUMENT)
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Daten werden bereitgestellt...'))
                sigIDs = [self.logger.database.getSignalID(
                    *i.split('.')) for i in self.signals_selected[chat_id]]
                xmin, xmax = self.signals_range[chat_id]
                dir = self.logger.config['global']['documentfolder']
                self.logger.database.signalsToCSV(
                    sigIDs, dir+'/telegram_export', xmin, xmax, database=True)
                bot.send_document(chat_id=chat_id, document=open(
                    dir+'/telegram_export.csv', 'rb'))
                bot.send_document(chat_id=chat_id, document=open(
                    dir+'/telegram_export.txt', 'rb'))
            else:
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Signalnamen bestehen aus \n<Gerät>.<Signal>\n. Deine Nachricht sah nicht so aus.\n'))
            self.signalsHandler(bot, chat_id, True)
            return

    def signalsSelectRangeHandler(self, bot, chat_id):
        self.mode[chat_id] = "signalSelectRange"
        xmin = self.logger.database.getGlobalXmin()
        xmax = self.logger.database.getGlobalXmax()
        xmin = dt.datetime.fromtimestamp(xmin).strftime("%d.%m.%Y %H:%M:%S")
        xmax = dt.datetime.fromtimestamp(xmax).strftime("%d.%m.%Y %H:%M:%S")
        xmin_s, xmax_s = self.signals_range[chat_id]
        xmin_s = dt.datetime.fromtimestamp(xmin_s).strftime("%d.%m.%Y %H:%M:%S")
        xmax_s = dt.datetime.fromtimestamp(xmax_s).strftime("%d.%m.%Y %H:%M:%S")
        text = 'Hier kannst du einstellen, welchen Bereich ich darstellen soll.\nGib dazu jetzt das Startdatum und Enddatum in folgendem Format ein: "' + \
            dt.datetime.fromtimestamp(time.time()-1000).strftime("%d.%m.%Y %H:%M:%S") + \
            ' - '+dt.datetime.fromtimestamp(time.time()).strftime("%d.%m.%Y %H:%M:%S")+'"'
        text += translate('telegram', '\nAusgewählter Zeitraum:\n')+xmin_s+' - '+xmax_s+'.\n'
        text += translate('telegram', 'Verfügbarer Zeitraum:\n')+xmin+' - '+xmax+'.\n'
        commands = [translate('telegram', 'Letzte Minute'), translate('telegram', 'Letzten 10 Minuten'), translate('telegram', 'Letzte Stunde'), translate('telegram', 'Letzte 24h'), translate(
            'telegram', 'Letzte Woche'), translate('telegram', 'Letzter Monat'), translate('telegram', 'Alles')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def signalsSelectRangeHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.signalsHandler(bot, chat_id)
        else:
            if strung == translate('telegram', 'Letzte Minute'):
                xmax = time.time()
                xmin = xmax-60*1
            elif strung == translate('telegram', 'Letzten 10 Minuten'):
                xmax = time.time()
                xmin = xmax-60*10
            elif strung == translate('telegram', 'Letzte Stunde'):
                xmax = time.time()
                xmin = xmax-60*60*1
            elif strung == translate('telegram', 'Letzte 24h'):
                xmax = time.time()
                xmin = xmax-60*60*24
            elif strung == translate('telegram', 'Letzte Woche'):
                xmax = time.time()
                xmin = xmax-60*60*24*7
            elif strung == translate('telegram', 'Letzter Monat'):
                xmax = time.time()
                xmin = xmax-60*60*24*31
            elif strung == translate('telegram', 'Alles'):
                xmin = self.logger.database.getGlobalXmin()
                xmax = self.logger.database.getGlobalXmax()
            else:
                if len(strung.split('-')) == 2:
                    times = strung.split('-')
                    while times[0].endswith(' '):
                        times[0] = times[0][0:-1]
                    while times[0].startswith(' '):
                        times[0] = times[0][1:]
                    while times[1].endswith(' '):
                        times[1] = times[1][0:-1]
                    while times[0].startswith(' '):
                        times[1] = times[1][1:]
                    foundXmin = False
                    foundXmax = False
                    for format in ['%d.%m.%Y %H:%M:%S', '%d.%m %H:%M:%S', '%d.%m %H:%M', '%d.%m.%Y %H:%M', '%d.%m.%Y', '%d.%m']:
                        try:
                            xmin = dt.datetime.strptime(times[0], format).timestamp()
                            foundXmin = True
                            break
                        except Exception:
                            pass
                    for format in ['%d.%m.%Y %H:%M:%S', '%d.%m %H:%M:%S', '%d.%m %H:%M', '%d.%m.%Y %H:%M', '%d.%m.%Y', '%d.%m']:
                        try:
                            xmax = dt.datetime.strptime(times[1], format).timestamp()
                            foundXmax = True
                            break
                        except Exception:
                            pass

                    if not foundXmin or not foundXmax:
                        # print(traceback.format_exc())
                        self.send_message(chat_id=chat_id,
                                          text=translate('telegram', 'Bitte sende mir einen Zeitraum, den ich verstehen kann:\n')+'"'+dt.datetime.fromtimestamp(time.time()-1000).strftime("%d.%m.%Y %H:%M:%S")+' - '+dt.datetime.fromtimestamp(time.time()).strftime("%d.%m.%Y %H:%M:%S")+'"')
                        return
                else:
                    foundXmin = False
                    while strung.endswith(' '):
                        strung = strung[0:-1]
                    while strung.startswith(' '):
                        strung = strung[1:]
                    for format in ['%d.%m.%Y %H:%M:%S', '%d.%m %H:%M:%S', '%d.%m %H:%M', '%d.%m.%Y %H:%M', '%d.%m.%Y', '%d.%m']:
                        try:
                            xmin = dt.datetime.strptime(strung, format).timestamp()
                            xmax = time.time()
                            foundXmin = True
                            break
                        except Exception:
                            pass
                    if not foundXmin:
                        self.send_message(chat_id=chat_id,
                                          text=translate('telegram', 'Bitte sende mir einen Zeitraum, den ich verstehen kann:\n')+'"'+dt.datetime.fromtimestamp(time.time()-1000).strftime("%d.%m.%Y %H:%M:%S")+' - '+dt.datetime.fromtimestamp(time.time()).strftime("%d.%m.%Y %H:%M:%S")+'"')
                        return
            self.signals_range[chat_id] = [xmin, xmax]
            xmin = dt.datetime.fromtimestamp(xmin).strftime("%d.%m.%Y %H:%M:%S")
            xmax = dt.datetime.fromtimestamp(xmax).strftime("%d.%m.%Y %H:%M:%S")
            text = translate('telegram', 'Ausgewählter Zeitraum:\n')+xmin+' - '+xmax+'.'
            self.send_message(chat_id=chat_id,
                              text=text)
            self.signalsHandler(bot, chat_id)

    # dt.datetime.fromtimestamp(time.time()).strftime("%d.%m.%Y %H:%M:%S")

    def createEventHandler(self, bot, chat_id, deviceselect=None, quiet=False):
        self.mode[chat_id] = "createEvent"
        if deviceselect is None or quiet:
            commands = ['.'.join(a) for a in self.logger.database.signalNames()]
            commands.sort()
            if quiet:
                text = translate('telegram', deviceselect)
            else:
                text = translate('telegram', '''*Event oder Messwert erzeugen*\n
                Sende mir eine Nachricht, um ein Event zu erzeugen \n
                Schreibe die Nachricht Fett (*Text*) für eine Fehlermeldung und kursiv (_Text_) für eine Warnung. Normaler Text hat die Priorität 'Information'\n
                Du kannst mir auch Messwerte schicken (z.B. '5 V'). \n
                *Du kannst das Event/den Messwert auch einem Signal zuordnen, indem du ein Signal aus der Liste auswählst oder indem du einen Signalnamen angibst ('Beispiel.Signal').\n
                ''')
            self.sendMenuMessage(bot, chat_id, commands, text)
        else:
            self.selectedSignalForEvent = deviceselect
            bot.send_message(chat_id, text=translate(
                'telegram', "*Signal ausgewählt: ")+deviceselect+'*')

    def createEventHandlerAns(self, bot, chat_id, strung):
        if strung in ['.'.join(a) for a in self.logger.database.signalNames()]:
            self.createEventHandler(bot, chat_id, strung, False)
        elif len(strung.split('.')) == 2:
            self.createEventHandler(bot, chat_id, strung, False)
        elif strung == BACKBUTTON:
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
                #                   text=translate('telegram', 'Messwert gesendet.'))
                self.createEventHandler(bot, chat_id, translate(
                    'telegram', 'Messwert gesendet.'), True)
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
                #                   text=translate('telegram', 'Event gesendet.'))
                self.createEventHandler(bot, chat_id, translate(
                    'telegram', 'Event gesendet.'), True)
                return
            self.menuHandler(bot, chat_id)

    def settingsHandler(self, bot, chat_id):
        self.mode[chat_id] = "settings"
        commands = [translate('telegram', "Alle Daten löschen"), translate(
            'telegram', 'Aufzeichnungsdauer ändern'), translate(
                'telegram', 'Globale Samplerate ändern'), translate(
                'telegram', '**Server neustarten**')]
        if self.logger.config['tcp']['active']:
            commands += [translate('telegram', "TCP-Server: An")]
        else:
            commands += [translate('telegram', "TCP-Server: Aus")]
        # if self.logger.config['telegram']['active']:
        #     commands += [translate('telegram', "*Telegram-Bot: An (!)*")]
        # else:
        #     commands += [translate('telegram', "Telegram-Bot: Aus")]

        ipadress = urllib.request.urlopen('https://ident.me').read().decode('utf8')
        ipadress = translate('telegram', '\nIP-Adresse: ')+str(ipadress)
        obj_Disk = psutil.disk_usage('/')
        total = str(round(obj_Disk.total / (1024.0 ** 3), 3))
        used = str(round(obj_Disk.used / (1024.0 ** 3), 3))
        free = str(round(obj_Disk.free / (1024.0 ** 3), 3))
        diskspace = translate('telegram', '\nEs sind noch ')+free + translate('telegram',
                                                                              ' GB von ')+total + translate('telegram', ' GB verfügbar')
        size, maxsize, databaseSize = self.logger.database.getSignalSize()
        if self.logger.config['postgresql']['active']:
            commands += [translate('telegram', 'Datenbank herunterladen')]
            diskspace = diskspace + \
                translate('telegram', '\nMessdaten werden in SQL-Datenbank gesichert')
            diskspace += str(translate('telegram', '\nDatenbank verwendet...\n'))
            diskspace += str(translate('telegram', '\nGesamt: ')+databaseSize[0])
            diskspace += str(translate('telegram', '\nFür Signale: ')+databaseSize[2])
            diskspace += str(translate('telegram', '\nFür Events: ')+databaseSize[3])
        else:
            diskspace += translate('telegram', '\nEs sind ')+lib.bytes_to_str(size)+translate(
                'telegram', ' von ')+lib.bytes_to_str(maxsize)+translate('telegram', ' verfügbar')
        self.sendMenuMessage(bot, chat_id, commands, '*'+self.logger.config['global']['name']+translate(
            'telegram', '-Einstellungen*')+ipadress+diskspace)

    def settingsHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.menuHandler(bot, chat_id)
            return
        elif strung == translate('telegram', '**Alle Daten löschen**'):
            self.logger.clear(True)
        elif strung == translate('telegram', 'Alle Daten löschen'):
            #self.settingsHandler(bot, chat_id)
            text = translate('telegram', 'Möchtest du wirklich alle Daten löschen?')
            commands = [translate('telegram', '**Alle Daten löschen**')]
            self.sendMenuMessage(bot, chat_id, commands, text)
            return
        elif strung == translate('telegram', 'Aufzeichnungsdauer ändern'):
            self.mode[chat_id] = 'resize'
            self.resizeHandler(bot, chat_id)
            return
        elif strung == translate('telegram', 'Globale Samplerate ändern'):
            self.globalSamplerateHandler(bot, chat_id)
            return
        elif strung == translate('telegram', '**Server neustarten**'):
            os.system('sudo reboot')
            time.sleep(5)
            text = translate(
                'telegram', '**Da hat etwas nicht geklappt.**\nEntweder fehlen mir die nötigen Rechte, oder mein Zuhause ist kein Linux-Gerät.')
            self.send_message(chat_id, text)
            return
        elif strung == translate('telegram', "TCP-Server: An"):
            ok = self.logger.toggleTcpServer(False)
            start = False
            name = 'TCP-Server'
        elif strung == translate('telegram', "TCP-Server: Aus"):
            ok = self.logger.toggleTcpServer(True)
            start = True
            name = 'TCP-Server'
        elif strung == translate('telegram', "*Telegram-Bot: An (!)*"):
            ok = self.logger.toggleTelegramBot(False)
            start = False
            name = 'Telegram-Bot'
        elif strung == translate('telegram', "Telegram-Bot: Aus"):
            ok = self.logger.toggleTelegramBot(True)
            start = True
            name = 'Telegram-Bot'
        elif strung == translate('telegram', 'Datenbank herunterladen'):
            path = self.logger.config['global']['documentfolder']+'/'
            filepathes = self.logger.database.exportCSV(path+'telegram_export', True)
            for file in filepathes:
                bot.send_document(chat_id=chat_id, document=open(
                    file, 'rb'))

            self.send_message(chat_id, translate('telegram', 'Datenbank übertragen'))
            return
        else:
            self.settingsHandler(bot, chat_id)
            return

        if start:
            start = translate('telegram', '**gestartet**')
        else:
            start = translate('telegram', '**beendet**')
        if ok:
            text = name + translate('telegram', " wurde ")+start+'.'
        else:
            text = name + translate('telegram', " konnte nicht ")+start + \
                translate('telegram', ' werden.')

        self.send_message(chat_id, text)
        self.settingsHandler(bot, chat_id)

    def globalSamplerateHandler(self, bot, chat_id):
        self.mode[chat_id] = 'globalSamplerate'
        commands = ['0.1', '0.5', '1', '2', '5', '10']
        self.sendMenuMessage(bot, chat_id, commands, translate(
            'telegram', '*Samplerate für alle Geräte ändern*'))

    def globalSamplerateHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.settingsHandler(bot, chat_id)
        else:
            try:
                samplerate = float(strung)
                self.logger.setAllSamplerates(samplerate)
                self.send_message(chat_id,
                                  translate('telegram', 'Samplerate wurde geändert'))
                self.settingsHandler(bot, chat_id)
            except:
                print(traceback.format_exc())
                self.send_message(chat_id,
                                  translate('telegram', 'Ich habe deine Nachricht nicht verstanden'))

    def resizeHandler(self, bot, chat_id):
        commands = ['1', '10', '100', '1000', '10000',
                    '1000000', '250000', '500000', '750000', '1000000']
        plotLen = self.logger.config['global']['recordLength']
        size, maxsize, databaseSize = self.logger.database.getSignalSize()
        if self.logger.config['postgresql']['active']:
            text = translate(
                'telegram', "Die Aufzeichnungsdauer beeinflusst nicht die Aufzeichnungslänge in der Datenbank. Diese ist unbegrenzt. \nDerzeitige Aufzeichnungsdauer: ")+str(plotLen)
        else:
            text = translate('telegram', "Derzeitige Aufzeichnungsdauer: ") + \
                str(self.logger.config['global']['recordLength'])
        self.sendMenuMessage(bot, chat_id, commands, text)

    def resizeHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.settingsHandler(bot, chat_id)
        else:
            try:
                value = int(strung)
            except ValueError:
                logging.debug(traceback.format_exc())
                logging.error('Not a valid user input')
                value = None
            if value:
                self.send_message(chat_id=chat_id, text=translate(
                    'telegram', 'Aufzeichnungsdauer geändert'))
                self.logger.database.resizeSignals(value)
                self.settingsHandler(bot, chat_id)
            else:
                self.send_message(chat_id=chat_id,
                                  text=translate('telegram', 'Fehlerhafte Eingabe'))
                self.settingsHandler(bot, chat_id)

    def sendSignalPlot(self, bot, chat_id, signalnames, xmin_plot, xmax_plot):
        if plt is None:
            self.send_message(chat_id=chat_id,
                              text=translate('telegram', '**Ich konnte kein Bild erstellen.**\nDu musst auf meinem Server "matplotlib" und "tkinker" installieren.'))
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
            a = signalname.split('.')
            signal = self.logger.database.getSignal_byName(
                a[0], a[1], xmin=xmin_plot, xmax=xmax_plot, database=True, maxN=1000)
            # bot.send_chat_action(chat_id=chat_id,
            #                      action=ChatAction.UPLOAD_PHOTO)
            if signal is not None:
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
                        xfmt = mdates.DateFormatter(translate('telegram', '%d.%m %H:%M'))
                    else:
                        xfmt = mdates.DateFormatter(translate('telegram', '%d.%m %H:%M:%S'))
                    plt.plot(dates, list(signal[3]), label=signalname + '['+signal[4]+']')  # ,'-x')
                except Exception as error:
                    print(error)
                    print(traceback.format_exc())
                    logging.error(traceback.format_exc())

            proc = (idx+1)/len(signalnames)*100
            self.send_message(chat_id=chat_id,
                              text=translate('telegram', 'Plot zu ')+str(round(proc))+translate('telegram', '% abgeschlossen'))

        ax = plt.gca()
        plt.xlabel(translate('telegram', 'Zeit [s]'))
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
                line1 = translate('telegram', 'Dauer: ') + str(dt.timedelta(seconds=duration))
                line2 = str(sigLen) + translate('telegram', ' Messwerte')
            else:
                line1 = str(dt.timedelta(seconds=duration)) + '/ ~ ' + \
                    str(dt.timedelta(seconds=maxduration))
                line2 = str(sigLen)+"/"+str(self.logger.config['global']['recordLength'])

            line3 = str(round(sigLen/(xmax-xmin), 2)) + ' Hz'
            # count = 20
            # if sigLen <= count:
            #     count = sigLen
            # if count > 1:
            #     meaner = sigLen[-count:]
            #     diff = 0
            #     for idx, m in enumerate(meaner[:-1]):
            #         diff += meaner[idx+1]-m
            #     if diff != 0:
            #         line3 = str(round((len(meaner)-1)/diff, 2))+" Hz"
            #     else:
            #         line3 = "? Hz"
            # else:
            #     line3 = "? Hz"
            return line1+"\n"+line2 + "\n" + line3
        except Exception:
            print(traceback.format_exc())
            logging.debug(traceback.format_exc())
            logging.error('Formatting signal information failed.')
            return translate('telegram', '')

    def createSignalInfoStr(self, x, y):
        maxduration = round(self.calcMaxDuration(x[0], x[-1], len(x)))
        duration = round(x[-1]-x[0])
        try:
            if self.logger.config['postgresql']['active']:
                line1 = translate('telegram', 'Dauer: ') + str(dt.timedelta(seconds=duration))
                line2 = str(len(list(x))) + translate('telegram', ' Messwerte')
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
            return translate('telegram', 'Ich konnte leider keine Info zu diesem Signal erzeugen.')

    def checkShortcutButton(self):
        pass

    def createShortcutList(self, bot, chat_id, idx=0):
        liste = list(self.logger.config['telegram']['chat_ids'][str(chat_id)][1][idx])
        if idx == 1:
            for idx, name in enumerate(liste):
                liste[idx] = name.split('.')[1]
        return liste

    def addShortcut(self, bot, chat_id, strung):
        device = self.current_plugin[chat_id]
        call = self.current_call[chat_id]
        call = device+'.'+call
        if call not in self.logger.config['telegram']['chat_ids'][str(
                chat_id)][1]:

            self.mode[chat_id] = "shortcut"
            self.sendMenuMessage(bot, chat_id, [self.current_call[chat_id]], translate(
                'telegram', 'Bitte gib eine Bezeichnung für diesen Shortcut an.'))
        else:
            self.send_message(chat_id, translate(
                'telegram', 'Für diese Funktionen/ diesen Parameter besteht bereits ein Shortcut!'))
            self.deviceCallHandler(bot, chat_id, self.current_call[chat_id])

    def addShortcutAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.deviceCallHandler(bot, chat_id, self.current_call[chat_id])
        elif strung in self.menuCommands:
            self.send_message(chat_id, translate(
                'telegram', 'Du kannst den Shortcut nicht nach einem Eintrag im Hauptmenü benennen.'))
        elif strung in self.createShortcutList(bot, chat_id):
            self.send_message(chat_id, translate(
                'telegram', 'Bitte wähle eine andere Bezeichnung. Diese ist schon vergeben.'))
        else:
            chat_id = chat_id
            device = self.current_plugin[chat_id]
            call = self.current_call[chat_id]
            call = device+'.'+call
            # logging.debug(call)
            if call not in self.logger.config['telegram']['chat_ids'][str(chat_id)][1]:
                self.logger.config['telegram']['chat_ids'][str(chat_id)][1][0].append(strung)
                self.logger.config['telegram']['chat_ids'][str(chat_id)][1][1].append(call)
                self.send_message(chat_id, translate(
                    'telegram', 'Shortcut wurde erstellt'))
                self.logger.save_config()
            else:
                self.send_message(chat_id, translate(
                    'telegram', 'Für diese Funktionen/ diesen Parameter besteht bereits ein Shortcut!'))
            self.deviceCallHandler(bot, chat_id, None)
            if self.current_call[chat_id] is not None:
                if "()" in self.current_call[chat_id]:
                    self.deviceFunctionsHandler(bot, chat_id)
                else:
                    self.deviceParametersHandler(bot, chat_id)
            else:
                self.deviceCallHandler(bot, chat_id, None)

    def removeShortcut(self, bot, chat_id, strung):
        if self.current_call[chat_id] is not None:
            strung = self.current_call[chat_id]
            if strung in self.logger.config['telegram']['chat_ids'][str(chat_id)][1][0]:
                idx = self.logger.config['telegram']['chat_ids'][str(
                    chat_id)][1][0].index(strung)
                self.logger.config['telegram']['chat_ids'][str(
                    chat_id)][1][1].pop(idx)
                self.logger.config['telegram']['chat_ids'][str(
                    chat_id)][1][0].pop(idx)
                self.current_call[chat_id] = None
                self.menuHandler(bot, chat_id)
                self.logger.save_config()
            else:
                self.send_message(chat_id, translate(
                    'telegram', 'Tut mir leid, ich konnte diesen Shortcut nicht finden!'))
                self.menuHandler(bot, chat_id)
        else:
            self.send_message(chat_id, translate(
                'telegram', 'Tut mir leid, ich habe mich verlaufen!'))
            self.menuHandler(bot, chat_id)

    def callShortcut(self, bot, chat_id, strung):
        if strung in self.logger.config['telegram']['chat_ids'][str(chat_id)][1][0]:
            idx = self.logger.config['telegram']['chat_ids'][str(
                chat_id)][1][0].index(strung)
            call = self.logger.config['telegram']['chat_ids'][str(
                chat_id)][1][1][idx].split('.')
            self.current_plugin[chat_id] = call[0]
            self.current_call[chat_id] = call[1]
            self.deviceCallHandler(bot, chat_id, 'SHORTCUT')
        else:
            self.send_message(chat_id, translate(
                'telegram', 'Tut mir leid, ich konnte diesen Shortcut nicht finden!'))

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
        self.mode[chat_id] = "automation"
        commands = []
        if self.logger.config['global']['globalActionsActivated']:
            commands += [translate('telegram', "Globale Aktionen: An")]
        else:
            commands += [translate('telegram', "Globale Aktionen: Aus")]
        if self.logger.config['global']['globalEventsActivated']:
            commands += [translate('telegram', "Globale Events: An")]
        else:
            commands += [translate('telegram', "Globale Events: Aus")]
        commands += [translate('telegram', "Aktionen bearbeiten")]
        commands += [translate('telegram', "Events bearbeiten")]
        text = '# Automation'
        if not quiet:
            text += translate('telegram', '''
\n
Hier kannst du globale Events und Aktionen ansehen und bearbeiten.\n
Globale Events werden erzeugt, wenn eine angegebene Bedingung erfüllt wird. Beispielsweise 'Temperatur an Sensor X übersteigt 80°C'. Ist die Bedingung erfüllt, so wird das angegebene Event erzeugt. (Event=[Nachricht, Priorität, ID])
\n
Globale Aktionen werden ausgeführt, wenn ein Event mit einer angegebenen ID erzeugt wurde. Die Aktion besteht aus einem Stück Python-Code.
        ''')
        self.sendMenuMessage(bot, chat_id, commands, text)

    def automationHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.menuHandler(bot, chat_id)
            return
        elif strung == translate('telegram', "Globale Aktionen: An"):
            self.logger.config['global']['globalActionsActivated'] = False
        elif strung == translate('telegram', "Globale Aktionen: Aus"):
            self.logger.config['global']['globalActionsActivated'] = True
        elif strung == translate('telegram', "Globale Events: An"):
            self.logger.config['global']['globalEventsActivated'] = False
        elif strung == translate('telegram', "Globale Events: Aus"):
            self.logger.config['global']['globalEventsActivated'] = True
        elif strung == translate('telegram', "Aktionen bearbeiten"):
            ok = self.globalActionsHandler(bot, chat_id)
            return
        elif strung == translate('telegram', "Events bearbeiten"):
            ok = self.globalEventsHandler(bot, chat_id)
            return
        self.automationHandler(bot, chat_id, quiet=True)

        # self.send_message(chat_id, text)

    def globalEventsHandler(self, bot, chat_id):
        if chat_id not in self.signals_selected.keys():
            self.signals_selected[chat_id] = []
        self.helper[chat_id] = None
        self.mode[chat_id] = "globalEvents"
        commands = []
        text = translate('telegram', 'Globale Events')
        commands += self.logger.printGlobalEvents()
        commands += [translate('telegram', 'Neues Event anlegen')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalEventsHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.signals_selected[chat_id] = []
            self.automationHandler(bot, chat_id)
            return
        elif strung in self.logger.printGlobalEvents():
            self.signals_selected[chat_id] = strung
            self.globalEventHandler(bot, chat_id)
            return
        elif strung == translate('telegram', 'Neues Event anlegen'):
            text = 'Gib dem neuen Event einen Namen'
            self.send_message(chat_id, text)
        elif strung != '':
            self.logger.addGlobalEvent(strung)
            self.logger.saveGlobalEvents()
            self.globalEventsHandler(bot, chat_id)

    def globalEventHandler(self, bot, chat_id):
        self.mode[chat_id] = "globalEvent"
        name = self.signals_selected[chat_id].split(': ')
        event = self.logger.globalEvents[name[0]]
        # {'cond', 'text', 'priority', 'return', 'id', 'rising, 'sname', 'dname'}
        if event['priority'] == 0:
            prio = translate('telegram', 'Information')
        elif event['priority'] == 1:
            prio = translate('telegram', 'Warnung')
        else:
            prio = translate('telegram', 'Fehler')
        commands = []
        text = translate('telegram', '# Event: '+str(name[0])+'\nText: '+event['text']+'\nPriorität: '+prio +
                         '\nID: '+event['id']+'\nZuordnung: '+event['dname']+'.'+event['sname']+'\nBedingung: '+event['cond'])
        if event['active']:
            commands += [translate('telegram', 'Aktiv')]
        else:
            commands += [translate('telegram', 'Inaktiv')]
        commands += [translate('telegram', 'Bedingung ändern')]
        commands += [translate('telegram', 'Signalzuordnung ändern')]
        if event['rising']:
            commands += [translate('telegram', 'Rising')]
        else:
            commands += [translate('telegram', 'Falling')]
        commands += [translate('telegram', 'ID vergeben')]
        commands += [translate('telegram', 'Text ändern')]
        commands += [translate('telegram', 'Priorität: ')+prio]
        commands += [translate('telegram', 'Löschen')]
        commands += [translate('telegram', 'Testen')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalEventHandlerAns(self, bot, chat_id, strung):
        name = self.signals_selected[chat_id].split(': ')
        event = self.logger.globalEvents[name[0]]
        # {'cond', 'text', 'priority', 'return', 'id', 'rising, 'sname', 'dname'}

        if strung == BACKBUTTON and self.helper[chat_id] == None:
            self.helper[chat_id] = None
            self.globalEventsHandler(bot, chat_id)
            return
        elif strung == BACKBUTTON:
            self.helper[chat_id] = None
            self.globalEventHandler(bot, chat_id)
            return
        elif strung == translate('telegram', 'Aktiv'):
            self.logger.globalEvents[name[0]]['active'] = False
            self.logger.saveGlobalEvents()
        elif strung == translate('telegram', 'Inaktiv'):
            self.logger.globalEvents[name[0]]['active'] = True
            self.logger.saveGlobalEvents()
        elif strung == translate('telegram', 'Bedingung ändern'):
            self.helper[chat_id] = 'changeCondition'
            signals = self.logger.database.signalNames()
            text = translate('telegram', 'Verfügbare Signale:\n')
            text += '\n'.join(['.'.join(i)+'.latest' for i in signals])
            # self.send_message(chat_id, text)
            self.sendMenuMessage(bot, chat_id, [], text)
            return
        elif strung == translate('telegram', 'Signalzuordnung ändern'):
            self.helper[chat_id] = 'selectSignal'
            commands = ['.'.join(a) for a in self.logger.database.signalNames()]
            commands.sort()
            text = translate(
                'telegram', 'Wähle ein Signal aus oder gib einen neuen Signalnamen an.')
            self.sendMenuMessage(bot, chat_id, commands, text)
            return
        elif strung == translate('telegram', 'Falling'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['rising'] = True
            self.logger.saveGlobalEvents()
        elif strung == translate('telegram', 'Rising'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['rising'] = False
            self.logger.saveGlobalEvents()
        elif strung == translate('telegram', 'ID vergeben'):
            text = translate('telegram', 'Gib jetzt eine EventID ein.')
            self.send_message(chat_id, text)
            self.helper[chat_id] = 'editEventID'
            return
        elif strung == translate('telegram', 'Text ändern'):
            text = translate('telegram', 'Gib jetzt den Benachrichtigungstext ein.')
            self.send_message(chat_id, text)
            self.helper[chat_id] = 'editText'
            return
        elif strung == translate('telegram', 'Priorität: ')+translate('telegram', 'Information'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['priority'] = 1
            self.logger.saveGlobalEvents()
        elif strung == translate('telegram', 'Priorität: ')+translate('telegram', 'Warnung'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['priority'] = 2
            self.logger.saveGlobalEvents()
        elif strung == translate('telegram', 'Priorität: ')+translate('telegram', 'Fehler'):
            self.helper[chat_id] = None
            self.logger.globalEvents[name[0]]['priority'] = 0
            self.logger.saveGlobalEvents()
        elif strung == translate('telegram', 'Löschen'):
            self.helper[chat_id] = None
            self.logger.removeGlobalEvent(name[0])
            self.logger.saveGlobalEvents()
            self.globalEventsHandler(bot, chat_id)
            return
        elif strung == translate('telegram', 'Testen'):
            self.helper[chat_id] = None
            ok, text = self.logger.triggerGlobalEvent(name[0])
            if text is None:
                text = translate(
                    'telegram', 'Ich hatte nicht gedacht, dass du mich so in die Irre leiten kannst...')
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
            self.logger.globalEvents[name[0]]['condition'] = strung
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
        self.mode[chat_id] = "globalActions"
        commands = []
        text = translate('telegram', 'Globale Aktionen')
        commands += self.logger.printGlobalActions()

        commands += [translate('telegram', 'Neue Aktion anlegen')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalActionsHandlerAns(self, bot, chat_id, strung):
        if strung == BACKBUTTON:
            self.signals_selected[chat_id] = []
            self.automationHandler(bot, chat_id)
            return
        elif strung in self.logger.printGlobalActions():
            self.signals_selected[chat_id] = strung
            self.globalActionHandler(bot, chat_id)
            return
        elif strung == translate('telegram', 'Neue Aktion anlegen'):
            text = 'Gib der neuen Aktion einen Namen'
            self.send_message(chat_id, text)
        elif strung != '':
            self.logger.addGlobalAction(strung)
            self.logger.saveGlobalActions()
            self.globalActionsHandler(bot, chat_id)

    def globalActionHandler(self, bot, chat_id):
        self.mode[chat_id] = "globalAction"
        name = self.signals_selected[chat_id].split(' bei ')
        action = self.logger.globalActions[name[0]]
        # {'listenID', 'script', 'parameters'}
        commands = []
        text = translate('telegram', '# Aktion: '+str(name[0])+'\nEvent-ListenIDs: '+', '.join(
            action['listenID'])+'\nScript: \n'+action['script'])
        if action['active']:
            commands += [translate('telegram', 'Aktiv')]
        else:
            commands += [translate('telegram', 'Inaktiv')]
        commands += [translate('telegram', 'Code ändern')]
        commands += [translate('telegram', 'ID auswählen')]
        commands += [translate('telegram', 'Löschen')]
        commands += [translate('telegram', 'Testen')]
        self.sendMenuMessage(bot, chat_id, commands, text)

    def globalActionHandlerAns(self, bot, chat_id, strung):
        name = self.signals_selected[chat_id].split(' bei ')
        action = self.logger.globalActions[name[0]]

        if strung == BACKBUTTON and self.helper[chat_id] == None:
            self.helper[chat_id] = None
            self.globalActionsHandler(bot, chat_id)
            return
        elif strung == BACKBUTTON:
            self.helper[chat_id] = None
            self.globalActionHandler(bot, chat_id)
            return
        elif strung == translate('telegram', 'Aktiv'):
            self.helper[chat_id] = None
            self.logger.globalActions[name[0]]['active'] = False
            self.logger.saveGlobalActions()
        elif strung == translate('telegram', 'Inaktiv'):
            self.helper[chat_id] = None
            self.logger.globalActions[name[0]]['active'] = True
            self.logger.saveGlobalActions()
        elif strung == translate('telegram', 'Code ändern'):
            self.helper[chat_id] = 'changeCode'
            plugins = self.logger.getPluginDict()
            signals = self.logger.database.signalNames()
            text = translate('telegram', 'Verfügbare Signale:\n')
            text += '\n'.join(['.'.join(i)+'.latest' for i in signals])
            self.send_message(chat_id, text)
            for name in plugins.keys():
                if plugins[name]['status'] is True:
                    text = translate('telegram', name+' Parameter:\n')
                    text += '\n'.join([i[0] for i in plugins[name]['parameters']])
                    text += '\n\n'+name+translate('telegram', ' Funktionen:\n')
                    text += '\n'.join([i+'()' for i in plugins[name]['functions']])
                    self.send_message(chat_id, text)
            self.sendMenuMessage(bot, chat_id, [], translate('telegram', 'Code bearbeiten'))
            return
        elif strung == translate('telegram', 'ID auswählen'):
            self.helper[chat_id] = 'selectIDs'
            events = self.logger.database.getUniqueEvents(False)
            commands = []
            for key in events.keys():
                commands.append(key)
            text = translate(
                'telegram', 'Wähle Events aus, durch die diese Aktion ausgeführt werden soll.')
            self.sendMenuMessage(bot, chat_id, commands, text)
            return
        elif strung == translate('telegram', 'Löschen'):
            self.helper[chat_id] = None
            self.logger.removeGlobalAction(name[0])
            self.logger.saveGlobalActions()
            self.globalActionsHandler(bot, chat_id)
            return
        elif strung == translate('telegram', 'Testen'):
            self.helper[chat_id] = None
            ok, text = self.logger.triggerGlobalAction(name[0])
            if text is None:
                text = translate(
                    'telegram', 'Ich hatte nicht gedacht, dass du mich so in die Irre leiten kannst...')
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
        action = self.userActions[strung]
        ok, ans = self.logger.executeScript(action)
        if ok and len(ans) == 2:
            try:
                text = translate('telegram', 'Aktion erfolgreich ausgeführt')
                if ans[0] == 'picture':
                    bot.send_photo(chat_id=chat_id, photo=open(ans[1], 'rb'))
                elif ans[0] == 'document':
                    bot.send_document(chat_id=chat_id, document=open(
                        ans[1], 'rb'))
                elif ans[0] == 'text':
                    self.send_message(chat_id, ans[1])
            except:
                text = translate('telegram', 'Aktion ist fehlerhaft')
                self.send_message(chat_id, text)
        else:
            text = translate('telegram', 'Aktion ist fehlerhaft')
            self.send_message(chat_id, text)

        # Globale Events aktiv
        # Globale Aktionen aktiv
        # Events bearbeiten
        #         'Das ist das Event', wenn '4>1'
        #                 Bedingung ändern ... Texteingabe, Infos anfordern
        #                 Signalzuordnung ändern ... Liste mit Signalen
        #                 Rising/Falling True/False
        #                 ID vergeben ... IDs aller bekannten Events
        #                 Text ändern ... Textingabe
        #                 Priorität 0/1/2
        #                 löschen
        #                 testen
        #         ...
        #         ...
        #         ...
        #         Neues Globales Event erzeugen
        #                 Name angeben ...
        #
        # Aktionen bearbeiten
        #         'Aktionsname', ausführen bei ID 'testEvent'
        #                 Code ändern ... Texteingabe
        #                 IDs auswählen ... Auswahl und manuelle Eingabe
        #                 löschen
        #                 testen
        #         ...
        #         ...
        #         ...
        #         Neues Globales Event erzeugen
        #                 Name angeben ...
        #
        # <--
