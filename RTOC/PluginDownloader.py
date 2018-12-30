import sys
import os
from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QCoreApplication

#from urllib.request import Request, urlopen, urlretrieve
#from bs4 import BeautifulSoup
import json
import traceback
import markdown2
#import urllib.request
# import requests
import base64
try:
    from .data.lib import pyqt_customlib as pyqtlib
except ImportError:
    from data.lib import pyqt_customlib as pyqtlib

from github import Github

translate = QCoreApplication.translate

class PluginDownloader(QtWidgets.QWidget):
    def __init__(self, userpath, repo='Haschtl/RTOC-Plugins'):
        super(PluginDownloader, self).__init__()
        self.repo = None
        self.repoName = None
        self.onlinePlugins = []
        self.localPlugins = {}
        self.localPluginInfos = {}
        self.pluginInfos ={}
        self.userpath = userpath

        self.currentname = ''
        self.installed = False
        self.uptodate = False

        if getattr(sys, 'frozen', False):
            # frozen
            packagedir = os.path.dirname(sys.executable)
        else:
            # unfrozen
            packagedir = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(packagedir+"/data/ui/getPlugins.ui", self)

        self.pluginList.currentTextChanged.connect(self.loadPlugin)
        self.installButton.clicked.connect(self.installPlugin)
        self.removeButton.clicked.connect(self.removePlugin)
        self.loadRepo(repo)
        self.loadLocalPlugins(userpath)
        print(self.localPlugins)

    def loadLocalPlugins(self, userpath):
        self.localPlugins = {}
        self.localPluginInfos = {}
        sys.path.insert(0, userpath)
        import devices

        subfolders = [f.name for f in os.scandir(list(devices.__path__)[0]) if f.is_dir()]
        for folder in subfolders:
            if folder not in ['', '__pycache__', '.git']:
                a =__import__(devices.__name__+"."+ folder)
                #for finder, name, ispkg in loggerlib.iter_namespace(devices):
                #fullpath = pkgutil.extend_path(list(devices.__path__)[0], folder)
                #print(fullpath)
                #for finder, name, ispkg in pkgutil.iter_modules(fullpath,devices.__name__+'.'+folder+ "."):
                #for root, dirs, files in os.walklevel(list(devices.__path__)[0], level=1):
                for files in os.listdir(list(devices.__path__)[0]+"/"+folder):
                    if files.endswith('.py'):
                        name = devices.__name__+'.'+folder+"."+files.replace('.py','')
                        namesplit = name.split('.')
                        print(name)
                        if namesplit[-1] not in ["LoggerPlugin"]:
                            self.localPlugins[namesplit[-1]] = list(devices.__path__)[0]+'/'+folder
        for plug in self.localPlugins.keys():
            #localPluginInfos
            if os.path.exists(self.localPlugins[plug]+"/info.json"):
                with open(self.localPlugins[plug]+"/info.json") as f:
                    data = json.load(f)
                    self.localPluginInfos[plug] = data
            else:
                print('Plugin '+plug+' was not installed from any repository')
                self.localPluginInfos[plug] = False

    def loadRepo(self, repo):
        self.repoName = repo
        self.github = Github('RTOC-Downloader','thisissupersave123')
        self.repo = self.github.get_repo(self.repoName)
        dirs = self.repo.get_contents('')
        for dir in dirs:
            try:
                realdir = dir.path
                if realdir.find('.')==-1 and realdir != '__pycache__':
                    info = self.repo.get_contents(realdir+"/info.json")
                    data = json.loads(info.decoded_content.decode('utf-8'))
                    #print(data)
                    self.pluginInfos[realdir]=data
                    self.onlinePlugins.append(realdir)
            except:
                print(info.decoded_content.decode('utf-8'))
                tb = traceback.format_exc()
                #print(tb)
                print('Error in '+dir.path)

        for p in self.onlinePlugins:
            self.pluginList.addItem(p)

    def loadPlugin(self, strung):
        self.currentname = strung
        self.installed = False
        self.uptodate = False
        try:
            info = self.pluginInfos[strung]
            print(strung)
            strung = "#"+strung+"\n\n"
            strung += "### Version: "+info['version']
            if self.currentname in self.localPluginInfos.keys():
                self.installed = True
                if self.localPluginInfos[self.currentname] != False:
                    strung += ' (Installed: '+ self.localPluginInfos[self.currentname]['version']+')'
                else:
                    strung += ' (was not installed from repo)'
                if info['version'] == self.localPluginInfos[self.currentname]['version']:
                    self.uptodate = True
            strung += "\n\n"
            strung += "*OS:* "+info['OS']+"\n\n"
            strung += "*GUI:* "+str(info['GUI'])+"\n\n"
            strung += "###Info:\n"+info['Info'].replace('\n','\n\n')
        except:
            strung = "# Error loading description from repo\n\n"
            tb = traceback.format_exc()
            strung += tb

        self.pluginInfo.setText(markdown2.markdown(strung))

        if self.installed and self.uptodate:
            self.installButton.hide()
            self.removeButton.show()
        if self.installed and not self.uptodate:
            self.installButton.show()
            self.removeButton.show()
        if not self.installed:
            self.installButton.show()
            self.removeButton.hide()

    def installPlugin(self):
        strung = translate('Downloader',"Aktuelle Version: ")+self.pluginInfos[self.currentname]['version']
        if self.currentname in self.localPluginInfos.keys():
            self.installed = True
            if self.localPluginInfos[self.currentname] != False:
                strung += translate('Downloader',' (Installiert: ')+ self.localPluginInfos[self.currentname]['version']+')'
            else:
                strung += translate('Downloader',' (Wurde nicht mit der RTOC-Repository installiert)')
        ok = pyqtlib.alert_message("Install plugin", "Möchtest du wirklich "+self.currentname+ " installieren", strung)
        if ok:
            print('install')
            url = 'https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/'+self.repoName+'/tree/master/'+self.currentname
            print(url)
            #urllib.request.urlretrieve(url, self.userpath+'/temp.zip')

            # f = open(self.userpath+'/temp.zip','wb')
            # f.write(urllib.request.urlopen(url).read())
            # f.close()

            # r = requests.get(url)
            #
            # with open(self.userpath+'/temp.zip', "wb") as code:
            #     code.write(r.content)
            self.download_directory(self.currentname)
            print('Download finished')
            pyqtlib.info_message(translate('Downloader',"Fertig"), translate('Downloader',"Installation abgeschlossen"), translate('Downloader',"Bitte starte RTOC neu, um neue Plugins zu benutzen."))

            if self.localPluginInfos[self.currentname] != False:
                if self.localPluginInfos[self.currentname]['dependencies'] != []:
                    info = '\n'.join(self.localPluginInfos[self.currentname]['dependencies'])
                    pyqtlib.info_message(translate('Abhängigkeiten'), "Dieses plugin benötigt einige Abhängigkeiten, die mittels 'pip3 install PACKAGE' installiert werden müssen.", info)

    def removePlugin(self):
        ok = pyqtlib.alert_message(translate('Downloader',"Plugin entfernen"), translate('Downloader',"Möchtest du wirklich ")+self.currentname+ translate('Downloader'," entfernen"), "")
        if ok:
            print('remove')
            if os.path.exists(self.userpath+"/devices/"+self.currentname):
                import shutil
                shutil.rmtree(self.userpath+"/devices/"+self.currentname)
                #os.removedirs(self.userpath+"/devices/"+self.currentname)
            self.loadLocalPlugins(self.userpath)
            self.loadPlugin(self.currentname)

    def download_directory(self, server_path):
        "Download all contents at server_path with commit tag sha in the repository."
        contents = self.repo.get_dir_contents(server_path)
        if not os.path.exists(self.userpath+"/devices/"+self.currentname):
            os.mkdir(self.userpath+"/devices/"+self.currentname)
        for content in contents:
            print("Processing "+ content.path)
            if content.type == 'dir' and '__pycache__' not in content.path:
                if not os.path.exists(self.userpath+"/devices/"+content.path):
                    os.mkdir(self.userpath+"/devices/"+content.path)
                self.download_directory(content.path)
            elif '__pycache__' not in content.path:
                try:
                    path = content.path
                    file_content = self.repo.get_contents(path)
                    file_data = base64.b64decode(file_content.content)
                    file_out = open(self.userpath+"/devices/"+content.path, "w")
                    file_out.write(file_data.decode('utf-8'))
                    file_out.close()
                except IOError as exc:
                    print('Error processing %s: %s', content.path, exc)

        self.loadLocalPlugins(self.userpath)
        self.loadPlugin(self.currentname)
    # def read_url(self, url):
    #     url = url.replace(" ","%20")
    #     req = Request(url)
    #     a = urlopen(req).read()
    #     soup = BeautifulSoup(a, 'html.parser')
    #     x = (soup.find_all('a'))
    #     for i in x:
    #         file_name = i.extract().get_text()
    #         url_new = url + file_name
    #         url_new = url_new.replace(" ","%20")
    #         if len(file_name)>1:
    #             if(file_name[-1]=='/' and file_name[0]!='.'):
    #                 self.read_url(url_new+"/")
    #         print(url_new)

if __name__ == "__main__":
    import sys
    userpath = os.path.expanduser('~/.RTOC')
    if not os.path.exists(userpath):
       os.mkdir(userpath)
    if not os.path.exists(userpath+'/devices'):
        os.mkdir(userpath+'/devices')
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName('MyWindow')
    main = PluginDownloader(userpath)
    main.setWindowTitle("Plugin Downloader")
    main.show()

    sys.exit(app.exec_())
