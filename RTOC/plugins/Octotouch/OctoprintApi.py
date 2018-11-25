# -*- encoding: utf-8 -*-

import time
import traceback
from threading import Thread
import requests
import json
from io import StringIO


class OctoprintAPI():
    def __init__(self, octolink='127.0.0.1', apicode='', port=5000):
        self.octolink = octolink
        self.apicode = apicode
        self.port = port
        self.s = requests.Session()
        self.s.headers.update({'X-Api-Key': apicode,
                               'Content-Type': 'application/json'})

        # Base address for all the requests
        self.base_address = 'http://' + self.octolink + ':' + str(self.port)
        self.console_history = ""
        self.apistatus = "Running"  # Errors
        self.status = {"sd": {"ready": False},
                       "state": {"flags":
                                 {"closedOrError": False,
                                  "error": False,
                                  "operational": False,
                                  "paused": False,
                                     "printing": False,
                                     "ready": False,
                                     "sdReady": False},
                                 "text": "Operational"},
                       "temperature": {"bed": {"actual": -1, "offset": -1, "target": -1},
                                       "tool0": {"actual": -1, "offset": -1, "target": -1},
                                       "tool1": {"actual": -1, "offset": -1, "target": -1}}}
        self.job = {"job":
                    {"estimatedPrintTime": None,
                     "filament": {"length": None, "volume": None},
                        "file": {"date": None, "name": None, "origin": None, "path": None, "size": None},
                     "lastPrintTime": None},
                    "progress":
                        {"completion": None, "filepos": None, "printTime": None, "printTimeLeft": None},
                    "state": "Operational"}
        self.apijob = "Running"
        self.run = True
        self.stopMe = False
        self.runPause = 2.5
        #self.gcoder_thread = Thread(target=self.octothread)
        #self.gcoder_thread.start()

    def connectPrinter(self, port=None, baudrate=None, printer_profile=None, save=None, autoconnect=None):
        """
        Connects to the printer
        :param port: [Optional] port where the printer is connected (ie: COMx in Windows, /dev/ttyXX in Unix systems).
                if not specified the current selected port will be used or if no port is selected auto detection will
                be used
        :param baudrate: [Optional] baud-rate, if not specified the current baud-rate will be used ot if no baud-rate
                is selected auto detection will be used
        :param printer_profile: [Optional] printer profile to be used for the connection, if not specified the default
                one will be used
        :param save: [Optional] whether to save or not the connection settings
        :param autoconnect: [Optional] whether to connect automatically or not on the next Ocotprint start
        """
        data = {'command': 'connect'}
        if port is not None:
            data['port'] = port
        if baudrate is not None:
            data['baudrate'] = baudrate
        if printer_profile is not None:
            data['printerProfile'] = printer_profile
        if save is not None:
            data['save'] = save
        if autoconnect is not None:
            data['autoconnect'] = autoconnect
        self.post(data, adress="/api/connection")

    def setRunning(self, run=True):
        self.run = run
        if not run:
            self.apistatus = "stopped"
            self.apijob = "stopped"

    def post(self, data, adress="/api/connection", noerror=204):
        try:
            r = self.s.post(self.base_address + adress, json=data)
            if r.status_code != noerror:
                raise Exception(
                    "Error: {code} - {content}".format(code=r.status_code, content=r.content.decode('utf-8')))
            return True, r
        except:
            tb = traceback.format_exc()
            print(tb)
            print("TRACEBACK HAS BEEN IGNORED. HTTP-POST FAILED")
            return False, "Error posting "+str(adress)
            return False, r

    def get(self, path="api/connection"):
        try:
            r = self.s.get(self.base_address + str(path))
            data = r.content.decode('utf-8')
            io = StringIO(data)
            io = json.load(io)
            #io = json.loads(data)
            return True, io
        except:
            tb = traceback.format_exc()
            print(tb)
            print("TRACEBACK HAS BEEN IGNORED. HTTP-GET FAILED")
            return False, "Error getting "+str(path)

    def disconnectPrinter(self):
        data = {'command': 'disconnect'}
        self.post(data, adress="/api/connection")

    # Thread which collects data in "runPause"-Intervalls
    def octothread(self):
        while not self.stopMe:
            time.sleep(self.runPause/2)
            if self.run:
                self.getStatus()
                time.sleep(self.runPause/2)
                self.getJob()

# GET Functions to aquire octoprint-data
    def getStatus(self):
        ok, status = self.get("/api/printer")
        if ok:
            if "bed" not in status["temperature"]:
                status["temperature"]["bed"] = {"actual": -1, "offset": -1, "target": -1}
            if "tool0" not in status["temperature"]:
                status["temperature"]["tool0"] = {"actual": -1, "offset": -1, "target": -1}
            if "tool1" not in status["temperature"]:
                status["temperature"]["tool1"] = {"actual": -1, "offset": -1, "target": -1}
            self.status = status
            self.apistatus = "Running"
        else:
            self.apistatus = "Printer is not operational"
        return ok, status

    def getTemps(self):
        # returns all temperatures
        return self.status["temperature"]

    def getHottest(self):
        # return hottest NozzleTemp
        temp = self.getTemps()
        if "tool1" in temp:
            if temp["tool0"]["actual"] > temp["tool1"]["actual"]:
                return temp["tool0"]
            else:
                return temp["tool1"]
        else:
            return temp["tool0"]

    def isTempSet(self):
        temp = self.getTemps()
        if temp["bed"]["target"]+temp["tool0"]["target"]+temp["tool1"]["target"] > 0:
            return True
        else:
            return False

    def getJob(self):
        ok, job = self.get("/api/job")
        if ok:
            self.job = job
            self.apijob = "Running"
        else:
            self.apijob = "Error loading Job-JSON in /api/job"
        return ok, job

    def getPrintFiles(self):
        '''
        {
          "files": [
            {
              "name": "whistle_v2.gcode",
              "path": "whistle_v2.gcode",
              "type": "machinecode",
              "typePath": ["machinecode", "gcode"],
              "hash": "...",
              "size": 1468987,
              "date": 1378847754,
              "origin": "local",
              "refs": {
                "resource": "http://example.com/api/files/local/whistle_v2.gcode",
                "download": "http://example.com/downloads/files/local/whistle_v2.gcode"
              },
              "gcodeAnalysis": {
                "estimatedPrintTime": 1188,
                "filament": {
                  "length": 810,
                  "volume": 5.36
                }
              },
              "print": {
                "failure": 4,
                "success": 23,
                "last": {
                  "date": 1387144346,
                  "success": true
                }
              }
            },
            {
              "name": "whistle_.gco",
              "path": "whistle_.gco",
              "type": "machinecode",
              "typePath": ["machinecode", "gcode"],
              "origin": "sdcard",
              "refs": {
                "resource": "http://example.com/api/files/sdcard/whistle_.gco"
              }
            },
            {
              "name": "folderA",
              "path": "folderA",
              "type": "folder",
              "typePath": ["folder"],
              "children": [
                {
                  "name": "whistle_v2_copy.gcode",
                  "path": "whistle_v2_copy.gcode",
                  "type": "machinecode",
                  "typePath": ["machinecode", "gcode"],
                  "hash": "...",
                  "size": 1468987,
                  "date": 1378847754,
                  "origin": "local",
                  "refs": {
                    "resource": "http://example.com/api/files/local/folderA/whistle_v2_copy.gcode",
                    "download": "http://example.com/downloads/files/local/folderA/whistle_v2_copy.gcode"
                  },
                  "gcodeAnalysis": {
                    "estimatedPrintTime": 1188,
                    "filament": {
                      "length": 810,
                      "volume": 5.36
                    }
                  },
                  "print": {
                    "failure": 4,
                    "success": 23,
                    "last": {
                      "date": 1387144346,
                      "success": true
                    }
                  }
                }
              ]
            }
          ],
          "free": "3.2GB"
        }
        '''
        return self.get("/api/files")

    def getVersion(self):
        '''
        {
            "api": "0.1",
            "server": "1.1.0"
        }
        '''
        return self.get("/api/version")

    def getConnection(self):
        '''
        {
          "current": {
            "state": "Operational",
            "port": "/dev/ttyACM0",
            "baudrate": 250000,
            "printerProfile": "_default"
          },
          "options": {
            "ports": ["/dev/ttyACM0", "VIRTUAL"],
            "baudrates": [250000, 230400, 115200, 57600, 38400, 19200, 9600],
            "printerProfiles": [{"name": "Default", "id": "_default"}],
            "portPreference": "/dev/ttyACM0",
            "baudratePreference": 250000,
            "printerProfilePreference": "_default",
            "autoconnect": true
          }
        }
        '''
        return self.get("/api/connection")

# Executional functions
    def send_gcode(self, gcode):
        """
        Sends one or multiple comma separated G-codes to the printer
        :param gcode: G-Code/s to send as a list containing all the G-codes to send
        """
        data = {'commands': [gcode]}
        return self.post(data, adress="/api/printer/command")

    def move(self, **kwargs):
        x = kwargs.get('x', None)
        y = kwargs.get('y', None)
        z = kwargs.get('z', None)
        feedrate = kwargs.get('feedrate', None)
        mode = kwargs.get('mode', "rel")
        if mode == "abs":
            self.send_gcode("G90")
        else:
            self.send_gcode("G91")
        code = ""
        if x is not None:
            code = code+" X"+str(x)
        if y is not None:
            code = code+" Y"+str(y)
        if z is not None:
            code = code+" Z"+str(z)
        if code != "":
            if feedrate is not None:
                code = code+" F"+str(feedrate)
            return self.send_gcode("G1"+code)
        return "No direction specified"

    def move_material(self, len, feedrate=None):
        self.send_gcode("M83")
        code = " E"+str(len)
        if feedrate:
            code = code+" F"+str(feedrate)
        return self.send_gcode("G1"+code)

    def setFan(self, value=True):
        if value:
            return self.send_gcode("M106")
        else:
            return self.send_gcode("M107")

    def setNozzleTemp(self,temp, hotend=0):
        if type(temp)==int or type(temp)==float:
            self.changeTool(hotend)
            return self.send_gcode("M104 S"+str(temp))
        else:
            return -1

    def setBedTemp(self,temp=0):
        if type(temp)==int or type(temp)==float:
            return self.send_gcode("M140 S"+str(temp))
        else:
            return -1

    # def setNozzleTemp(self, temp=0, hotend=0):
    #     if type(temp) == float:
    #         temp = int(temp)
    #     if type(temp) == int:
    #         tool = "tool"+str(hotend)
    #         data = {'command': 'target', 'target': temp}
    #         return self.post(data, adress='/api/printer/'+tool)
    #     else:
    #         return("No valid integer was given")
    #
    # def setBedTemp(self, temp=0):
    #     # if type(temp)==int:
    #     #     return self.send_gcode("M140 S"+str(temp))
    #     # else:
    #     #     return "No valid integer was given"
    #     """
    #     Set the bed temperature
    #     :param temp: desired bed temperature
    #     """
    #     if type(temp) == float:
    #         temp = int(temp)
    #     if type(temp) == int:
    #         data = {'command': 'target', 'target': temp}
    #         return self.post(data, adress='/api/printer/bed')
    #     else:
    #         return("No valid integer was given")

    def home(self):
        return self.send_gcode("G28")

    def enginesOff(self):
        return self.send_gcode("M18")

    def resetEEPROM(self):
        return self.send_gcode("M502")

    def saveEEPROM(self):
        return self.send_gcode("M500")

    def loadEEPROM(self):
        return self.send_gcode("M501")

    def restart(self):
        return self.send_gcode("M999")

    def calibrateZ(self):  # setZzero
        self.send_gcode("M428")
        self.saveEEPROM()

    def setJob(self, command=None):
        if command in ["pause", "start", "cancel", "restart"]:
            data = {'command': str(command)}
            return self.post(data, adress='/api/job')
        else:
            return "please set command to one of these: pause, start, cancel"

    def select_file(self, file_name):
        data = {'command': 'select', 'print': False}
        return self.post(data, adress='/api/files/local/' + file_name, noerror=200)

    def slice_file(self, file_name):
        data = {'command': 'slice', 'select': True}
        return self.post(data, adress='/api/files/local/' + file_name, noerror=202)

    def changeTool(self, toolIndex):
        self.tool = toolIndex
        self.toolS = 'tool'+str(toolIndex)
        self.send_gcode("T"+str(toolIndex))
