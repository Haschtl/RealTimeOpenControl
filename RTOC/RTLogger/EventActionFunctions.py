#!/usr/local/bin/python3
# coding: utf-8
import os
import json
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

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


class EventActionFunctions:
    """
    This class contains all global event/action-specific functions of RTLogger
    """

    def loadGlobalEvents(self):
        """
        Loads global events from file and stores them in dict 'self.globalEvents'
        """
        print('Loading global events from file')
        userpath = os.path.expanduser(self.config['global']['documentfolder'])
        if not os.path.exists(userpath):
            os.mkdir(userpath)

        if os.path.exists(userpath+"/globalEvents.json"):
            try:
                with open(userpath+"/globalEvents.json", encoding="UTF-8") as jsonfile:
                    self.globalEvents = json.load(jsonfile, encoding="UTF-8")
            except:
                self.globalEvents = {}
                logging.error('Error in GlobalEvents-JSON-File')
                return
        else:
            self.globalEvents = {
                "myevent1": {
                    "cond": "Generator.Square.latest >= 2",
                    "text": "It is big",
                    "return": " ",
                    "priority": 0,
                    "id": "testID",
                    'trigger': 'rising',
                    'sname': '',
                    'dname': '',
                    'active': True
                }
            }
            return

        empty = {
            "cond": "",
            "text": "",
            "return": " ",
            "priority": 0,
            "id": "",
            'trigger': 'rising',
            'sname': '',
            'dname': '',
            'active': False
        }
        # for name in self.globalEvents.keys():
        #     tmp = self.globalEvents[name]
        #     self.globalEvents[name] = empty
        #     for key in tmp.keys():
        #         self.globalEvents[name][key] = tmp[key]

    def saveGlobalEvents(self):
        """
        Saves global events from 'self.globalEvents' to file.
        """
        print('Saving global events to file')
        with open(self.config['global']['documentfolder']+"/globalEvents.json", 'w', encoding="utf-8") as fp:
            json.dump(self.globalEvents, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def checkGlobalEvents(self, events):
        """
        Checks if events are valid. Will add the key 'errors' to each event. 'errors' will be True, if it's not valid.

        Args:
            events (dict): events to be checked.

        Returns:
            events (dict): Input-events + 'errors'-key
        """
        #print('Check, if global events are valid')
        for key in events.keys():
            events[key]['errors'] = False
        return events

    def performGlobalEvents(self, y, unit, devicename, signalname, x=None):
        """
        Performs global events, if their conditions are fullfilled. This function is called any time data is added to signals.

        Args:
            y (float): y-value of signal (not needed)
            unit (str): unit of signal (not needed)
            devicename (str): devicename of signal
            signalname (str): signalname of signal
            x (float): x-value of signal (not needed)

        """
        events = self.checkGlobalEvents(self.globalEvents)
        for key in events.keys():
            event = events[key]
            # if event['errors'] == False 
            if devicename+"."+signalname in event["cond"] and event['active']:
                ok, cond = self.checkCondition(event['cond'])
                if ok:
                    cond = bool(cond)

                    if key not in self.activeGlobalEvents.keys():
                        self.activeGlobalEvents[key] = event
                        self.activeGlobalEvents[key]['latest'] = None
                        print('First time for  this event')

                    triggered = False
                    if event['trigger']=='true':
                        if cond is True:
                            triggered = True
                    elif event['trigger'] == 'false':
                        if cond is False:
                            triggered = True
                    else:
                        if cond is True and self.activeGlobalEvents[key]['latest'] is not True:
                            if event['trigger']=='rising' or event['trigger']=='both':
                                triggered = True
                        elif cond is False and self.activeGlobalEvents[key]['latest'] is True:
                            logging.info('Event-Ende: '+devicename+"."+signalname+': '+event['text'])
                            if event['trigger']=='falling' or event['trigger']=='both':
                                triggered = True

                    if triggered:
                        self.database.addNewEvent(
                            text=event['text'], sname=event['sname'], dname=event['dname'], value=event['return'], priority=event['priority'], id=event['id'])

                    self.activeGlobalEvents[key]['latest'] = cond
                else:
                    print('ERROR:\n'+cond)

    def resetGlobalEventState(self):
        self.activeGlobalEvents = {}
        
    def loadGlobalActions(self):
        """
        Loads global actions from file and stores them in dict 'self.globalActions'
        """
        print('Loading global actions from file')
        userpath = self.config['global']['documentfolder']
        if not os.path.exists(userpath):
            os.mkdir(userpath)
        if os.path.exists(userpath+"/globalActions.json"):
            try:
                with open(userpath+"/globalActions.json", encoding="UTF-8") as jsonfile:
                    self.globalActions = json.load(jsonfile, encoding="UTF-8")
            except Exception:
                self.globalActions = {}
                logging.error('Error in GlobalActions-JSON-File')
                return
        else:
            self.globalActions = {"action2": {
                "listenID": [
                    "testID"
                ],
                "parameters": "",
                "script": "Generator.gen_level = 1",
                "active": False
            }
            }
            return

        empty = {
            "listenID": [],
            "parameters": "",
            "script": "",
            "active": False
        }
        # for name in self.globalActions.keys():
        #     tmp = self.globalActions[name]
        #     self.globalActions[name] = empty
        #     for key in tmp.keys():
        #         self.globalActions[name][key] = tmp[key]

    def saveGlobalActions(self):
        """
        Saves global actions from 'self.globalActions' to file.
        """
        print('Saving global actions to file')
        with open(self.config['global']['documentfolder']+"/globalActions.json", 'w', encoding="utf-8") as fp:
            json.dump(self.globalActions, fp,  sort_keys=False, indent=4, separators=(',', ': '))

    def checkGlobalActions(self, actions):
        """
        Checks if actions are valid. Will add the key 'errors' to each event. 'errors' will be True, if it's not valid.

        Args:
            actions (dict): actions to be checked.

        Returns:
            actions (dict): Input-actions + 'errors'-key
        """
        # print('Check, if actions are valid')
        for key in actions.keys():
            action = actions[key]
            actions[key]['errors'] = False
            for value in action.keys():
                if value in ['parameters', 'script']:
                    if type(action[value]) != str:
                        actions[key]['errors'] = True
                elif value in ['listenID']:
                    if type(action[value]) is str:
                        actions[key][value] = [actions[key][value]]
                elif value != 'errors':
                    actions[key]['errors'] = True
        return actions

    def performGlobalActions(self, id, value):
        actions = self.checkGlobalActions(self.globalActions)
        for key in actions.keys():
            action = actions[key]
            # if action['errors'] is False:
            for actionId in action['listenID']:
                if actionId == id and action['active']:
                    # Execute action
                    ok, prints = self.executeScript(action['script'])
                    print('Performing global action for eventID: ' +
                            str(id)+' with value: '+str(value))
                    print('Action is: '+str(action)+', Execution: '+str(ok))
                    print('Returns:' + str(prints))
                    if not ok:
                        break

    def editGlobalEvent(self, name='testEvent', cond='', text='TestEvent', priority=0, retur='', id='testID', trigger='rising', sname='', dname='', active=True):
        self.globalEvents[name] = {'cond': cond, 'text': text,
                                   'priority': priority, 'return': retur, 'id': id, 'trigger': trigger, 'sname': sname, 'dname': dname, 'active': active}


    def editGlobalAction(self, name='testAction', listenID='testID', script='', parameters='', active=True):
        if type(listenID) == str:
            listenID = [listenID]
        self.globalActions[name] = {'listenID': listenID,
                                    'script': script, 'parameters': parameters, 'active': active}

    def addGlobalEvent(self, name='testEvent', cond='', text='TestEvent', priority=0, retur='', id='testID', trigger='rising', sname='', dname='', active=True):
        countname = name
        i = 2
        while countname in self.globalEvents.keys():
            countname = name+str(i)
            i += 1
        name = countname
        self.globalEvents[name] = {'cond': cond, 'text': text,
                                   'priority': priority, 'return': retur, 'id': id, 'trigger': trigger, 'sname': sname, 'dname': dname, 'active': active}

    def addGlobalAction(self, name='testAction', listenID='testID', script='', parameters='', active=True):
        countname = name
        i = 2
        while countname in self.globalEvents.keys():
            countname = name+str(i)
            i += 1
        name = countname
        if type(listenID) == str:
            listenID = [listenID]
        self.globalActions[name] = {'listenID': listenID,
                                    'script': script, 'parameters': parameters, 'active': active}
                                    
    # def addGlobalAction(self, name='testAction', listenID='testID', script='', parameters='', active=True):
    #     countname = name
    #     i = 2
    #     while countname in self.globalEvents.keys():
    #         countname = name+str(i)
    #         i += 1
    #     name = countname
    #     if type(listenID) == str:
    #         listenID = [listenID]
    #     self.globalActions[name] = {'listenID': listenID,
    #                                 'script': script, 'parameters': parameters, 'active': active}

    def removeGlobalAction(self, key):
        if key in self.globalActions.keys():
            self.globalActions.pop(key)
            return True
        else:
            return False

    def removeGlobalEvent(self, key):
        if key in self.globalEvents.keys():
            self.globalEvents.pop(key)
            return True
        if key in self.activeGlobalEvents.keys():
            self.activeGlobalEvents.pop(key)
        else:
            return False

    def printGlobalEvents(self, wo=True):
        strung = []
        for name in self.globalEvents.keys():
            event = self.globalEvents[name]
            if event['cond'] != '':
                strung.append(name+': '+event['cond'])
            else:
                strung.append(name+': '+translate('RTOC', 'No condition'))
        return strung

    def printGlobalActions(self):
        strung = []
        for name in self.globalActions.keys():
            event = self.globalActions[name]
            if event['listenID'] != []:
                strung.append(name+': '+', '.join(event['listenID']))
            else:
                strung.append(name+': '+translate('RTOC', 'No event connected'))
        return strung

    def triggerGlobalEvent(self, key):
        if key in self.globalEvents.keys():
            event = self.globalEvents[key]
            ok, cond = self.checkCondition(event['cond'])
            if ok:
                # cond = bool(cond)
                text = translate('RTOC', 'Condition is valid\nAnswer: ')+str(cond)
                self.database.addNewEvent(text=event['text'], sname=event['sname'], dname=event['dname'],
                                          value=event['return'], priority=event['priority'], id=event['id'])
                return True, text
            else:
                text = translate('RTOC', 'Condition is invalid!\nAnswer: ')+str(cond)
                return False, text
        return False, None

    def triggerGlobalAction(self, key):
        if key in self.globalActions.keys():
            action = self.globalActions[key]
            ok, prints = self.executeScript(action['script'])
            if ok:
                text = translate('RTOC', 'Action is valid\nAnswer: ')+str(prints)
                return True, text
            else:
                text = translate('RTOC', 'Action is invalid!\nAnswer: ')+str(prints)
                return False, text
        return False, None
