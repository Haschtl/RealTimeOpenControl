import sys
import os
# from PyQt5 import QtCore
from PyQt5 import uic
from PyQt5 import QtWidgets  # , QtGui
from PyQt5.QtCore import QCoreApplication

import json
import traceback
import urllib.request
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    import markdown2
except ImportError:
    markdown2 = None

try:
    from github import Github
except ImportError:
    Github = None
    logging.error('Github for python not installed. Please install with "pip3 install pyGithub"')

from ..lib import pyqt_customlib as pyqtlib

if True:
    translate = QCoreApplication.translate

    def _(text):
        return translate('downloader', text)
else:
    import gettext
    _ = gettext.gettext


class PluginDownloader(QtWidgets.QWidget):
    def __init__(self, userpath, repo='Haschtl/RTOC-Plugins', selfself=None):
        super(PluginDownloader, self).__init__()
        self.self = selfself
        self.repo = None
        self.repoName = None
        self.onlinePlugins = []
        self.localPlugins = {}
        self.localPluginInfos = {}
        self.pluginInfos = {}
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
        uic.loadUi(packagedir+"/ui/getPlugins.ui", self)

        self.pluginList.currentTextChanged.connect(self.loadPlugin)
        self.installButton.clicked.connect(self.installPlugin)
        self.removeButton.clicked.connect(self.removePlugin)
        self.loadRepo(repo)
        self.loadLocalPlugins(userpath)
        logging.info(self.localPlugins)

    def loadLocalPlugins(self, userpath):
        self.localPlugins = {}
        self.localPluginInfos = {}
        sys.path.insert(0, userpath)
        import devices

        subfolders = [f.name for f in os.scandir(list(devices.__path__)[0]) if f.is_dir()]
        for folder in subfolders:
            if folder not in ['', '__pycache__', '.git']:
                a = __import__(devices.__name__+"." + folder)
                for files in os.listdir(list(devices.__path__)[0]+"/"+folder):
                    if files.endswith('.py'):
                        name = devices.__name__+'.'+folder+"."+files.replace('.py', '')
                        namesplit = name.split('.')
                        logging.debug(name)
                        if namesplit[-1] not in ["LoggerPlugin"]:
                            self.localPlugins[namesplit[-1]] = list(devices.__path__)[0]+'/'+folder
        for plug in self.localPlugins.keys():
            # localPluginInfos
            if os.path.exists(self.localPlugins[plug]+"/info.json"):
                try:
                    with open(self.localPlugins[plug]+"/info.json") as f:
                        data = json.load(f)
                        self.localPluginInfos[plug] = data
                except Exception:
                    logging.debug(traceback.format_exc())
                    logging.error('Error loading local plugin info: '+str(plug))
                    self.localPluginInfos[plug] = ''
            else:
                logging.error('Plugin '+plug+' was not installed from any repository')
                self.localPluginInfos[plug] = False

    def loadRepo(self, repo):
        self.repoName = repo
        if Github is not None:
            self.github = Github('RTOC-Downloader', 'thisissupersave123')
            self.repo = self.github.get_repo(self.repoName)
            dirs = self.repo.get_contents('')
            for dir in dirs:
                try:
                    realdir = dir.path
                    if realdir.find('.') == -1 and realdir != '__pycache__':
                        info = self.repo.get_contents(realdir+"/info.json")
                        data = json.loads(info.decoded_content.decode('utf-8'))
                        self.pluginInfos[realdir] = data
                        self.onlinePlugins.append(realdir)
                except Exception:
                    logging.debug(traceback.format_exc())
                    logging.debug(info.decoded_content.decode('utf-8'))
                    logging.error('Error in '+dir.path)

        for p in self.onlinePlugins:
            self.pluginList.addItem(p)

    def loadPlugin(self, strung):
        self.currentname = strung
        self.installed = False
        self.uptodate = False
        try:
            info = self.pluginInfos[strung]
            strung = "#"+strung+"\n\n"
            strung += "### Version: "+info['version']
            if self.currentname in self.localPluginInfos.keys():
                self.installed = True
                if self.localPluginInfos[self.currentname] != False:
                    strung += ' (Installed: ' + \
                        self.localPluginInfos[self.currentname]['version']+')'
                else:
                    strung += ' (was not installed from repo)'
                if info['version'] == self.localPluginInfos[self.currentname]['version']:
                    self.uptodate = True
            strung += "\n\n"
            strung += "*OS:* "+info['OS']+"\n\n"
            strung += "*GUI:* "+str(info['GUI'])+"\n\n"
            strung += "###Info:\n"+info['Info'].replace('\n', '\n\n')
        except Exception:
            logging.debug(traceback.format_exc())
            strung = "# Error loading description from repo\n\n"
            tb = traceback.format_exc()
            strung += tb
        if markdown2 is not None:
            self.pluginInfo.setText(markdown2.markdown(strung))
        else:
            self.pluginInfo.setText(strung)

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
        strung = translate('RTOC', "Current version: {}").format(self.pluginInfos[self.currentname]['version'])
        if self.currentname in self.localPluginInfos.keys():
            self.installed = True
            if self.localPluginInfos[self.currentname] != False:
                strung += translate('RTOC', ' (Installed: {})').format(self.localPluginInfos[self.currentname]['version'])
            else:
                strung += translate('RTOC', ' (Was not installed with the RTOC repository)')
        ok = pyqtlib.alert_message(translate('RTOC', "Install plugin"), translate('RTOC', "Do you really want to install {}?").format(self.currentname), strung)
        if ok:
            logging.info('install')
            url = 'https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/' + \
                self.repoName+'/tree/master/'+self.currentname
            logging.info(url)
            self.download_directory(self.currentname)
            logging.info('Download finished')
            pyqtlib.info_message(translate('RTOC', "Finished"), translate('RTOC', "Installation completed"), translate('RTOC', "Please restart RTOC."))
            if self.self:
                self.self.reloadDevices()

            if self.localPluginInfos[self.currentname] != False:
                if self.localPluginInfos[self.currentname]['dependencies'] != []:
                    info = '\n'.join(self.localPluginInfos[self.currentname]['dependencies'])
                    pyqtlib.info_message(translate('RTOC', 'Dependencies'), translate('RTOC', "This plugin needs dependencies that can be installed using 'pip3 install PACKAGE'."), info)

    def removePlugin(self):
        ok = pyqtlib.alert_message(translate('RTOC', "Remove plugin"), translate('RTOC', "Dou you really want to remove {}?").format(self.currentname), "")
        if ok:
            logging.info('remove')
            if os.path.exists(self.userpath+"/devices/"+self.currentname):
                import shutil
                shutil.rmtree(self.userpath+"/devices/"+self.currentname)
                # os.removedirs(self.userpath+"/devices/"+self.currentname)
            self.loadLocalPlugins(self.userpath)
            self.loadPlugin(self.currentname)
            if self.self:
                self.self.reloadDevices()

    def download_directory(self, server_path):
        "Download all contents at server_path with commit tag sha in the repository."
        contents = self.repo.get_dir_contents(server_path)
        if not os.path.exists(self.userpath+"/devices/"+self.currentname):
            os.mkdir(self.userpath+"/devices/"+self.currentname)
        for content in contents:
            logging.info("Processing " + content.path)
            if content.type == 'dir' and '__pycache__' not in content.path:
                if not os.path.exists(self.userpath+"/devices/"+content.path):
                    os.mkdir(self.userpath+"/devices/"+content.path)
                self.download_directory(content.path)
            elif '__pycache__' not in content.path:
                try:
                    path = content.path
                    url = content.download_url
                    urllib.request.urlretrieve(url, self.userpath+"/devices/"+path)
                except IOError as exc:
                    logging.debug(traceback.format_exc())
                    logging.error('Error processing %s: %s', content.path, exc)

        self.loadLocalPlugins(self.userpath)
        self.loadPlugin(self.currentname)


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
