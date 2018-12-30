# -*- encoding: utf-8 -*-

import os
import re
import datetime
import sys
import subprocess
import json
from shutil import copy
from collections import defaultdict
import requests
from urllib.parse import urlparse
from urllib.request import urlopen
import cgi

# Type functions

define = ""

def  bytes_to_str(size):
    #2**10 = 1024
    size = int(size)
    power = 2**10
    n = 0
    Dic_powerN = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /=  power
        n += 1
    return str(round(size,2))+' '+Dic_powerN[n]+'B'

def identifyElementTypeFromString(string):
    if isInt(string):
        return "int", int(string)
    elif isFloat(string):
        return "float", float(string)
    elif isBoolean(string):
        return "boolean", convertBoolean(string)
    elif isLink(string):
        return "link", string
    elif isFile(string):
        return "file", string
    elif isPathS(string):
        return "pfad", string[8:]
    elif isDate(string):
        return "date", str2date(string)
    else:
        return "string", string

def identifyElementType(element):
    if type(element) == list:
        return "list", element
    elif type(element) == int:
        return "int", element
    elif type(element) == float:
        return "float", element
    elif type(element) == bool:
        return "boolean", element
    else:
        if type(element) == str:
            if isFile(element):
                return "file", element
            else:
                return "string", element
        else:
            #logging("Unknown TagType")
            return "string", str(element)


def isInt(s):
    try:
        int(s)
        return True
    except:
        return False


def isPath(s):
    try:
        if not os.path.isabs(s):
            config=load_config()
            s = config["current_project_path"]+"/"+define.media_path+s
        #if os.path.exists(os.path.dirname(s)):
        if os.path.exists(s):
            return True
        else:
            return False
    except:
        return False


def isPathS(s):
    if s.find("file:///") is 0:
        return True
    else:
        return False


def isFloat(s):
    try:
        float(s)
        return True
    except:
        return False


def isBoolean(s):
    if s.lower() in ["true", "ja", "yes"] or s.lower() in ["false", "nein", "no"]:
        return True
    else:
        return False

def convertBoolean(s):
    if s.lower() in ["true", "ja", "yes"]:
        return True
    else:
        return False

def isLink(s):
    if findURLs(s) is not []:
        return False #True
    else:
        return False

def isPicture(s):
    if isFile(s):
        formats = [".jpg", ".png", ".tiff", ".jpeg", ".svg", ".gif", ".ico"]
        for format in formats:
            if s.lower().endswith(format):
                return True
    return False

def isFile(s):
    try:
        if not os.path.isabs(s):
            config=load_config()
            s = config["current_project_path"]+"/"+define.media_path+s
        if os.path.exists(s):
            return True
        else:
            return False
    except:
        return False

# download functions

def findURLs(string):
    # findall() has been used
    # with valid conditions for urls in string
    url = re.findall(
        'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)
    return url

def is_downloadable(url):
    """
    Does the url contain a downloadable resource
    """
    h = requests.head(url, allow_redirects=True)
    header = h.headers
    content_type = header.get('content-type')
    if 'text' in content_type.lower():
        return False
    if 'html' in content_type.lower():
        return False
    return True


def getURLFilename(url):

    try:
        remotefile = urlopen(url)
        blah = remotefile.info()['Content-Disposition']
        value, params = cgi.parse_header(blah)
        filename = params["filename"]
        return filename
    except:
        a = urlparse(url)
        return os.path.basename(a.path)


def downloadFile(self, link, newDir):
    if is_downloadable(link):
        filename = getURLFilename(link)
        uniq_filename = str(datetime.datetime.now().date())
        date_filename = filename.replace(".", uniq_filename+".")
        with open(newDir+date_filename, 'wb') as f:
            r = requests.get(link, allow_redirects=True)
            total_length = r.headers.get('content-length')

            if total_length is None:
                f.write(r.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in r.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    self.ddone = int(50 * dl / total_length)
                    sys.stdout.write("\r[%s%s]" % ('=' * self.ddone, ' ' * (50-self.ddone)))
                    sys.stdout.flush()
        if date_filename is filename:
            self.delementType = "string"
            self.delementContent = link
            return "string", link
        if isPicture(filename):
            self.delementType = "datei"
            self.delementContent = newDir+date_filename
            return "bild", newDir+date_filename
        else:
            self.delementType = "datei"
            self.delementContent = newDir+date_filename
            return "datei", newDir+date_filename
    else:
        self.delementType = "string"
        self.delementContent = link
        return "string", link

# File functions

def copyFileRand(origFile, newDir):
    filename = os.path.basename(origFile)
    if newDir+filename is not origFile:
        copy(origFile, newDir)
    return newDir+filename

def openFile(filepath):
    print("Opening file: "+filepath)
    try:
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name is 'nt':
            os.startfile(filepath)
        elif os.name is 'posix':
            subprocess.call(('xdg-open', filepath))
        return True
    except:
        #logging("Der angegebenen Datei ist keine Anwendung zugeordnet: "+filepath)
        return False

# List functions

def list_duplicates(seq):
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key, locs) for key, locs in tally.items()
            if len(locs) > 1)


def column(matrix, i):
    # Returns eevery i-th element in array [[i1,...],[i2,...]...]
    ans = []
    for row in matrix:
        if i<len(row):
            ans.append(row[i])
    return ans
#    return [row[i] for row in matrix]

def indexes(list, element):
    return [i for i, e in enumerate(list) if e == element]

# Other Functions

def date2str(date):  # date=[Year, Month, Day, Hour, Minute, Second]
    if date and len(date) is 3 and type(date[0]) is int and type(date[1]) is int and type(date[2]) is int:
        now = datetime.datetime.now()
        if date is [now.year, now.month, now.day]:
            return "heute"
        elif date is [now.year, now.month, now.day-1] or date is [now.year, now.month - 1, now.day+30]:
            return "gestern"
        else:
            return str(date[2])+"."+str(date[1])+"."+str(date[0])
    elif date and len(date) is 6 and type(date[0]) is int and type(date[1]) is int and type(date[2]) is int and type(date[3]) is int and type(date[4]) is int and type(date[5]) is int:
        now = datetime.datetime.now()
        # for i in [3,4,5]:
        #     if date[i]<10:
        #         date[i]="0"+str(date[i])
        return str(date[2])+"."+str(date[1])+"."+str(date[0])+" "+str(date[3])+":"+str(date[4])+":"+str(date[5])
    else:
        return "Wrong date format to print"

def isDate(string):
    try:
        datetime.datetime.strptime(string, '%d.%m.%Y %H:%M:%S')
        print("IsLongDate")
        return True
    except:
        try:
            datetime.datetime.strptime(string, '%d.%m.%Y')
            print("IsShortDate")
            return True
        except:
            return False

def str2date(string):
    stringsplit=string.split(" ")
    if len(stringsplit)==2:
        d=datetime.datetime.strptime(string, '%d.%m.%Y %H:%M:%S')
        date=[d.year, d.month, d.day]
        time=[d.hour, d.minute, d.second]
        return date+time
    elif len(stringsplit)==1:
        d=datetime.datetime.strptime(string, '%d.%m.%Y')
        date=[d.year, d.month, d.day]
        return date+[0,0,0]
    else:
        return [0,0,0,0,0,0]

def clearLog():
    os.remove("ProFiler.log")

def logging(string,dlevel=3):
    #dlevel=min(define.debug_level,dlevel)
    if dlevel==1:
        print(string)
    elif dlevel==2:
        logToFile(string)
    elif dlevel==3:
        print(string)
        logToFile(string)

def logToFile(string):
    now = datetime.datetime.now()
    datestr = date2str([now.year, now.month, now.day])
    with open("ProFiler.log", "a") as myfile:
        myfile.write(datestr+" "+str(string)+"\n")

def load_config():
    with open("data/config.json", encoding="UTF-8") as jsonfile:
        config = json.load(jsonfile, encoding="UTF-8")
    newlist = []
    for path in config["last_project_pathes"]:
        if os.path.exists(path):
            newlist.append(path)
    config["last_project_pathes"] = newlist
    #logging('config loaded')
    return config
