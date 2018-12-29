import time
import logging
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater
from telegram import KeyboardButton, ReplyKeyboardMarkup, ChatAction, Bot, ParseMode
from threading import Thread
from io import BytesIO
try:
    import matplotlib.pyplot as plt
except ImportError:
    print('Could not import matplotlib.pyplot\nThis happens if matplotlib or tkinker isn\'t installed. \nReceiving plots via telegram is disabled.')
    plt = None

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtCore import QObject
translate = QCoreApplication.translate

messageIntervall = 1

try:
    from .data.lib import general_lib as lib
except ImportError:
    from data.lib import general_lib as lib

def first_lower(s):
    if len(s) == 0:
        return s
    else:
        return s[0].lower() + s[1:]


class bufferMessage():
    def __init__(self, config):
        self.config = config
        self.lastbot = None
        self.lastchat = None
        self.running = True
        self.buffer = ''
        self.start()

    def start(self):
        try:
            self.bot = Bot(self.config['telegram_token'])
            #Thread.__init__(self)
        except:
            print('Starting Telegram-Bot failed, maybe wrong telegram-token')
            print(self.config['telegram_token'])

    def send_long_message(self, message_text='Empty message', chat_id=None):
        self.lastchat = chat_id
        if chat_id not in self.config['telegram_chat_ids'] and chat_id is not None:
            self.config['telegram_chat_ids'].append(chat_id)
        for id in self.config['telegram_chat_ids']:
            self.bot.send_message(chat_id=id, text=message_text, parse_mode=ParseMode.MARKDOWN)


class telegramBot(QObject):
    def __init__(self, logger):
        self.logger = logger
        self.config = self.logger.config
        self.menuCommands = [translate('telegram', 'Event-Benachrichtigung festlegen'), translate(
            'telegram', 'Letzte Messwerte'), translate('telegram', 'Signale'), translate('telegram', 'Geräte'), translate('telegram', 'Event erzeugen')]
        self.mode = {}
        self.selectedSignalForEvent = None
        self.servername = self.config['telegram_name']
        self.token = self.config['telegram_token']
        self.eventlevel = self.config['telegram_eventlevel']

        self.sender = bufferMessage(self.config)
        # self.sender.setName('buffer_sender')
        self.updater = None
        self.current_plugin = {}
        self.current_call = {}

    def setToken(self, token):
        self.token = token
        self.config['telegram_token'] = token

    def sendMessage(self, message):
        if self.sender.running:
            t = Thread(target=self.sender.send_long_message,args=(str(message),))
            t.start()
            return True
        else:
            return False

    def connect(self):
        idler = Thread(target=self.connectThread)
        idler.start()
        return True

    def connectThread(self):
        try:
            self.updater = Updater(token=self.token)
            self.dispatcher = self.updater.dispatcher
            logging.basicConfig(
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

            echo_handler = MessageHandler(Filters.text, self.textHandler)
            self.dispatcher.add_handler(echo_handler)
            self.updater.start_polling()
            print('Telegram-Server successfully started!')
            self.updater.idle()
            if self.config['telegram_eventlevel'] <= 1:
                self.sender.send_long_message(self.servername+' wurde gestartet')
            return True
        except:
            return False

    def stop(self):
        print('Telegram-Server stopped!')
        self.sender.running = False
        if self.updater:
            self.updater.stop()

#################### Action Handler #################################################

    def addCmd(self, name, command):  # Create CommandHandler and add to dispatcher
        def cmd(bot, update):
            bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)
            command(bot, update)
        handler = CommandHandler(name, cmd)
        self.dispatcher.add_handler(handler)


# SHELL HANDLER
    def textHandler(self, bot, update):
        if update.message.chat_id not in self.config['telegram_chat_ids'] and update.message.chat_id is not None:
            self.config['telegram_chat_ids'].append(update.message.chat_id)
        if update.message.chat_id not in self.mode.keys():
            self.mode[update.message.chat_id] = 'menu'
            self.current_plugin[update.message.chat_id] = None
            self.current_call[update.message.chat_id] = None

        strung = update.message.text
        if self.mode[update.message.chat_id] == "adjustEventNotification":
            if strung in self.adjustEventNotificationCommands:
                i = self.adjustEventNotificationCommands.index(strung)
                if i <= 3:
                    self.config['telegram_eventlevel'] = i
                    bot.send_message(chat_id=update.message.chat_id,
                                     text=translate('telegram', 'Einstellung angepasst'))
                self.mode[update.message.chat_id] = ''
                self.menuHandler(bot, update)
        elif self.mode[update.message.chat_id] == "menu":
            if strung == translate('telegram', 'Event-Benachrichtigung festlegen'):
                self.mode[update.message.chat_id] = "adjustEventNotification"
                self.adjustEventNotificationHandler(bot, update)
            elif strung == translate('telegram', 'Letzte Messwerte'):
                self.sendLatest(bot, update.message.chat_id)
                self.menuHandler(bot, update)
            elif strung == translate('telegram', 'Geräte'):
                self.mode[update.message.chat_id] = "plugins"
                self.pluginsHandler(bot, update)
            elif strung == translate('telegram', "Signale"):
                self.mode[update.message.chat_id] = "signals"
                self.signalsHandler(bot, update)
            elif strung == translate('telegram', 'Event erzeugen'):
                self.mode[update.message.chat_id] = "createEvent"
                self.createEventHandler(bot, update)
            else:
                self.menuHandler(bot, update)
        elif self.mode[update.message.chat_id] == 'signals':
            if strung == translate('telegram', 'Signale löschen'):
                self.logger.clear()
                self.menuHandler(bot, update)
            elif strung == translate('telegram', 'Aufzeichnungsdauer ändern'):
                self.mode[update.message.chat_id] = 'resize'
                self.resizeHandler(bot, update)
            elif strung == translate('telegram', '<-- Zurück'):
                self.menuHandler(bot, update)
            else:
                self.sendSignalPlot(bot, update, strung)
                self.signalsHandler(bot, update)
        elif self.mode[update.message.chat_id] == 'resize':
            if strung == translate('telegram', '<-- Zurück'):
                self.mode[update.message.chat_id] = 'signals'
                self.signalsHandler(bot, update)
            else:
                try:
                    value = int(strung)
                except:
                    value = None
                if value:
                    bot.send_message(chat_id=update.message.chat_id, text=translate(
                        'telegram', 'Aufzeichnungsdauer geändert'))
                    self.logger.resizeSignals(value)
                    self.mode[update.message.chat_id] = 'signals'
                    self.signalsHandler(bot, update)
                else:
                    bot.send_message(chat_id=update.message.chat_id,
                                     text=translate('telegram', 'Fehlerhafte Eingabe'))
                    self.mode[update.message.chat_id] = 'signals'
                    self.signalsHandler(bot, update)
        elif self.mode[update.message.chat_id] == "createEvent":
            if strung in ['.'.join(a) for a in self.logger.signalNames]:
                self.mode[update.message.chat_id] = "createEvent"
                self.createEventHandler(bot, update, strung)
            elif strung == translate('telegram', '<-- Zurück'):
                self.selectedSignalForEvent = None
                self.menuHandler(bot, update)
            else:
                bot.send_message(chat_id=update.message.chat_id, text=translate(
                    'telegram', 'Event gesendet.'))
                if self.selectedSignalForEvent != None:
                    signal = self.selectedSignalForEvent.split('.')
                    device = signal[0]
                    signal = signal[1]
                    self.selectedSignalForEvent = None
                else:
                    device = 'Telegram'
                    signal = str(update.message.chat_id)
                self.logger.addNewEvent(strung,signal, device)
                self.menuHandler(bot, update)
        elif self.mode[update.message.chat_id] == 'plugins':
            if strung in self.logger.devicenames.keys():
                self.pluginHandler(bot, update, strung)
                self.mode[update.message.chat_id] = 'plugin'
            else:
                self.menuHandler(bot, update)
        elif self.mode[update.message.chat_id] == 'plugin':
            commands = []
            if self.logger.pluginStatus[self.current_plugin[update.message.chat_id]] == True:
                commands += [translate('telegram', "Gerät beenden")]
            elif self.logger.pluginStatus[self.current_plugin[update.message.chat_id]] == False:
                commands += [translate('telegram', "Gerät starten")]
            else:
                commands += [translate('telegram', "Gerätefehler")]
            commands += [translate('telegram', "Funktionen"), translate('telegram', "Parameter")]
            if strung in commands:
                if strung == translate('telegram', "Gerät beenden"):
                    self.logger.stopPlugin(self.current_plugin[update.message.chat_id])
                    self.pluginHandler(bot, update, self.current_plugin[update.message.chat_id])
                elif strung == translate('telegram', "Gerät starten"):
                    self.logger.startPlugin(self.current_plugin[update.message.chat_id])
                    self.pluginHandler(bot, update, self.current_plugin[update.message.chat_id])
                elif strung == translate('telegram', "Funktionen"):
                    self.mode[update.message.chat_id] = 'pluginfunctions'
                    self.pluginfunctionsHandler(bot, update)
                elif strung == translate('telegram', "Parameter"):
                    self.mode[update.message.chat_id] = 'pluginparameters'
                    self.pluginparametersHandler(bot, update)
            elif strung == translate('telegram', "<-- Zurück"):
                self.mode[update.message.chat_id] = "plugins"
                self.current_plugin[update.message.chat_id] = None
                self.pluginsHandler(bot, update)
            else:
                self.pluginHandler(bot, update, self.current_plugin[update.message.chat_id])
        elif self.mode[update.message.chat_id] == 'pluginfunctions':

            commands = []
            name = self.current_plugin[update.message.chat_id]
            for fun in self.logger.pluginFunctions.keys():
                if fun.startswith(name+".") and fun not in [name+".close", name+".loadGUI", name+".createTCPClient", name+".sendTCP", name+".plot", name+".setDeviceName", name+".event", name+".stream"]:
                    commands += [fun.replace(name+".", '')+'()']

            if strung in commands:
                print(strung)
                self.current_call[update.message.chat_id] = strung
                self.mode[update.message.chat_id] = "call"
                self.plugincallHandler(bot, update)
            elif strung == translate('telegram', "<-- Zurück"):
                self.mode[update.message.chat_id] = "plugin"
                self.current_call[update.message.chat_id] = None
                self.pluginHandler(bot, update, self.current_plugin[update.message.chat_id])
            else:
                self.pluginfunctionsHandler(bot, update)
        elif self.mode[update.message.chat_id] == 'pluginparameters':
            commands = []
            name = self.current_plugin[update.message.chat_id]
            for fun in self.logger.pluginParameters.keys():
                if fun.startswith(name+".") and fun not in [name+".deviceName", name+".close", name+".run", name+".smallGUI", name+".sock", name+".widget"]:
                    commands += [fun.replace(name+".", '')]

            if strung in commands:
                print(strung)
                self.current_call[update.message.chat_id] = strung
                self.mode[update.message.chat_id] = "call"
                self.plugincallHandler(bot, update)
            elif strung == translate('telegram', "<-- Zurück"):
                self.mode[update.message.chat_id] = "plugin"
                self.current_call[update.message.chat_id] = None
                self.pluginHandler(bot, update, self.current_plugin[update.message.chat_id])
            else:
                self.pluginparametersHandler(bot, update)
        elif self.mode[update.message.chat_id] == 'call':
            if strung == translate('telegram', "<-- Zurück"):
                self.current_call[update.message.chat_id] = None
                if "()" in self.current_call[update.message.chat_id]:
                    self.mode[update.message.chat_id] = "pluginfunctions"
                    self.pluginfunctionsHandler(bot, update)
                else:
                    self.mode[update.message.chat_id] = "pluginparameters"
                    self.pluginparametersHandler(bot, update)
            else:
                if "()" in self.current_call[update.message.chat_id]:
                    self.temp = []
                    try:
                        exec('self.temp = ['+strung+"]")
                    except:
                        print("this was not a python-type: "+strung)
                    self.logger.callPluginFunction(
                        self.current_plugin[update.message.chat_id], self.current_call[update.message.chat_id], *self.temp)
                else:
                    value = strung
                    self.logger.getPluginParameter(self.current_plugin[update.message.chat_id], self.current_call[update.message.chat_id], value)
                self.current_call[update.message.chat_id] = None
                self.mode[update.message.chat_id] = "plugin"
                self.pluginHandler(bot, update, self.current_plugin[update.message.chat_id])
        else:
            if strung and strung != "":
                bot.send_message(chat_id=update.message.chat_id, text=translate(
                    'telegram', 'Wenn dein Text aussieht, wie eine JSON, dann kannst du damit später alles machen'))
            else:
                bot.send_message(chat_id=update.message.chat_id, text=translate(
                    'telegram', 'Was soll ich dazu sagen ...'))
            self.menuHandler(bot, update)

# MENU FUNCTIONS
    def sendSignalPlot(self, bot, update, signalname):
        bio = BytesIO()
        bio.name = 'image.png'
        a = signalname.split('.')
        data = self.logger.getSignal(self.logger.getSignalId(a[0], a[1]))

        # Make a square figure and axes
        if plt != None:
            plt.gcf().clear()
            plt.plot(data[0], data[1])
            plt.xlabel(translate('telegram', 'Zeit [s]'))
            plt.savefig('telegram_export.png')
            plt.title(signalname)
            t = self.createToolTip(self.logger.getSignalId(a[0], a[1]))
            print(t)
            bot.send_photo(chat_id=update.message.chat_id, photo=open('telegram_export.png', 'rb'))
            bot.send_message(chat_id=update.message.chat_id, text=t)
        else:
            bot.send_message(chat_id=update.message.chat_id, text='Could not send plot.\n This happens, if matplotlib or tkinker isn\'t installed. on the RTOC-Server\n')

    def createToolTip(self, id):
        maxduration = self.calcDuration(list(self.logger.getSignal(id)[0]))
        duration = self.logger.getSignal(id)[0][-1]-self.logger.getSignal(id)[0][0]
        try:
            line1 = time.strftime("%H:%M:%S", time.gmtime(int(duration))) + \
                "/~"+time.strftime("%H:%M:%S", time.gmtime(int(maxduration)))
            line2 = str(
                len(list(self.logger.getSignal(id)[0])))+"/"+str(self.logger.maxLength)
            count = 20
            if len(self.logger.getSignal(id)[0]) <= count:
                count = len(self.logger.getSignal(id)[0])
            if count > 1:
                meaner = list(self.logger.getSignal(id)[0])[-count:]
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
        except:
            return "Tooltip failed"

    def build_menu(self, buttons, n_cols, header_buttons=None, footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    def resizeHandler(self, bot, update):
        commands = []
        commands.append(translate('telegram', '<-- Zurück'))
        button_list = [KeyboardButton(s) for s in commands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        size, maxsize = self.logger.getSignalSize()
        bot.send_message(update.message.chat_id, text=translate(
            'telegram', "Derzeitige Aufzeichnungsdauer: ")+str(self.logger.maxLength)+translate(
                'telegram', '\nSignale verwenden ')+lib.bytes_to_str(size)+'/'+lib.bytes_to_str(maxsize), reply_markup=reply_markup)

    def pluginsHandler(self, bot, update):
        commands = list(self.logger.devicenames)
        commands.append(translate('telegram', '<-- Zurück'))
        button_list = [KeyboardButton(s) for s in commands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, text=translate(
            'telegram', "Geräte"), reply_markup=reply_markup)

    def createEventHandler(self, bot, update, deviceselect=None):
        if deviceselect == None:
            commands = ['.'.join(a) for a in self.logger.signalNames]
            commands += [translate('telegram', '<-- Zurück')]
            button_list = [KeyboardButton(s) for s in commands]
            reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
            bot.send_message(update.message.chat_id, text=translate(
                'telegram', "Neues Event erzeugen\nSende eine Nachricht, um ein Event zu erzeugen.\nWähle ein Signal aus, um das Event einem Signal zuzuordnen."), reply_markup=reply_markup)
        else:
            self.selectedSignalForEvent = deviceselect
            bot.send_message(update.message.chat_id, text=translate(
                'telegram', "Signal ausgewählt: ")+deviceselect)

    def signalsHandler(self, bot, update):
        commands = ['.'.join(a) for a in self.logger.signalNames]
        commands += [translate('telegram', 'Signale löschen'), translate('telegram',
                                                                         'Aufzeichnungsdauer ändern'), translate('telegram', '<-- Zurück')]
        button_list = [KeyboardButton(s) for s in commands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, text=translate(
            'telegram', "Geräte"), reply_markup=reply_markup)

    def pluginHandler(self, bot, update, device):
        commands = []
        if self.logger.pluginStatus[device] == True:
            commands += [translate('telegram', "Gerät beenden")]
        elif self.logger.pluginStatus[device] == False:
            commands += [translate('telegram', "Gerät starten")]
        else:
            commands += [translate('telegram', "Gerätefehler")]
        commands += [translate('telegram', "Funktionen"), translate('telegram',
                                                                    "Parameter"), translate('telegram', "<-- Zurück")]
        button_list = [KeyboardButton(s) for s in commands]
        self.current_plugin[update.message.chat_id] = device
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, text=device, reply_markup=reply_markup)

    def pluginparametersHandler(self, bot, update):
        commands = []
        name = self.current_plugin[update.message.chat_id]
        for fun in self.logger.pluginParameters.keys():
            if fun.startswith(name+".") and fun not in [name+".deviceName", name+".close", name+".run", name+".smallGUI", name+".sock", name+".widget"]:
                commands += [fun.replace(name+".", '')]
        commands += [translate('telegram', "<-- Zurück")]
        button_list = [KeyboardButton(s) for s in commands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, text=name+' Parameter', reply_markup=reply_markup)

    def pluginfunctionsHandler(self, bot, update):
        commands = []
        name = self.current_plugin[update.message.chat_id]
        for fun in self.logger.pluginFunctions.keys():
            if fun.startswith(name+".") and fun not in [name+".close", name+".loadGUI", name+".createTCPClient", name+".sendTCP", name+".plot", name+".setDeviceName", name+".event", name+".stream"]:
                commands += [fun.replace(name+".", '')+'()']
        commands += [translate('telegram', "<-- Zurück")]
        button_list = [KeyboardButton(s) for s in commands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, text=name +
                         translate('telegram', " Funktionen"), reply_markup=reply_markup)

    def plugincallHandler(self, bot, update):
        commands = []
        commands += [translate('telegram', "<-- Zurück")]
        if "()" in self.current_call[update.message.chat_id]:
            infotext = translate('telegram', "Bitte gib Parameter an, falls benötigt")
        else:
            value = self.logger.getPluginParameter(self.current_plugin[update.message.chat_id], "get", [self.current_call[update.message.chat_id]])
            if value != False:
                infotext = translate(
                    'telegram', "Bitte gib einen neuen Wert an.\nDerzeitiger Wert: ") + str(value)
            else:
                infotext = translate('telegram', "Fehler")
        button_list = [KeyboardButton(s) for s in commands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, text=infotext, reply_markup=reply_markup)

    def menuHandler(self, bot, update):
        self.mode[update.message.chat_id] = 'menu'
        button_list = [KeyboardButton(s) for s in self.menuCommands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, text=translate(
            'telegram', "Hauptmenü"), reply_markup=reply_markup)

    def adjustEventNotificationHandler(self, bot, update):
        self.mode[update.message.chat_id] = "adjustEventNotification"
        self.adjustEventNotificationCommands = [translate('telegram', "Alle Benachrichtigungen"), translate('telegram', "Warnungen"), translate(
            'telegram', "Nur Fehlermeldungen"),  translate('telegram', "Keine Benachrichtigung"), translate('telegram', "<-- Zurück")]
        button_list = [KeyboardButton(s) for s in self.adjustEventNotificationCommands]
        reply_markup = ReplyKeyboardMarkup(self.build_menu(button_list, n_cols=1))
        bot.send_message(update.message.chat_id, translate('telegram', 'Wähle eine Benachrichtigungsstufe aus. Derzeitige Stufe:\n') +
                         self.adjustEventNotificationCommands[self.config['telegram_eventlevel']], reply_markup=reply_markup)

    def sendLatest(self, bot, chat_id):
        strung = ""
        namelist = self.logger.signalNames
        for idx, signal in enumerate(namelist):
            if signal != ['RTOC', '']:
                value = self.logger.getSignal(self.logger.getSignalId(signal[0], signal[1]))[1][-1]
                unit = self.logger.getSignalUnits(self.logger.getSignalId(signal[0], signal[1]))
                strung = strung+signal[0]+'.'+signal[1]+': '+str(value)+" "+str(unit)+"\n"
        if strung == "":
            strung = translate('telegram', "Keine Messwerte vorhanden")
        self.sender.send_long_message(strung, chat_id)

    def calcDuration(self, x):
        if len(x) > 2:
            dt = x[-1]-x[0]
            l = len(x)
            maxlen = self.logger.maxLength
            return dt/l*maxlen
        else:
            return -1
