# -*- encoding: utf-8 -*-
"""
This module contains some helper functions.
"""
import os
import re
import datetime
import sys
import subprocess
from shutil import copy
from collections import defaultdict
import requests
from urllib.parse import urlparse
from urllib.request import urlopen
import cgi
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)
# Type functions

if True:
    from PyQt5 import QtCore 
    translate = QtCore.QCoreApplication.translate

    def _(text):
        return translate('rtoc', text)
else:
    import gettext
    _ = gettext.gettext

define = ""


def bytes_to_str(size):
    """
    Returns a string representing the size.

    Args:
        size (int): The number of bytes to be converted to a string.

    Returns:
        string
    """
    # 2**10 = 1024
    size = int(size)
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2))+' '+Dic_powerN[n]+'B'


def identifyElementTypeFromString(string):
    """
    Returns a tuple ("type", value). type represents the datatype, value is the transformed string

    Args:
        string (str): The string to be converted.

    Returns:
        bool
    """
    if isInt(string):
        return "int", int(string)
    elif isFloat(string):
        return "float", float(string)
    elif isBoolean(string):
        return "boolean", convertBoolean(string)
    elif isLink(string):
        return "link", string
    else:
        return "string", string


def isInt(string):
    """
    Check if string can be converted to integer

    Args:
        string (str): The string to be checked.

    Returns:
        bool
    """
    try:
        int(string)
        return True
    except ValueError:
        return False


def isFloat(string):
    """
    Check if string can be converted to float

    Args:
        string (str): The string to be checked.

    Returns:
        bool
    """
    try:
        float(string)
        return True
    except ValueError:
        return False


def isBoolean(s):
    """
    Check if string can be converted to bool

    Args:
        string (str): The string to be checked.

    Returns:
        bool
    """
    if s.lower() in ["true", "ja", "yes"] or s.lower() in ["false", "nein", "no"]:
        return True
    else:
        return False


def convertBoolean(string):
    """
    Convert a string to bool.

    Args:
        string (str): The string to be converted.

    Returns:
        bool
    """
    if string.lower() in ["true", "ja", "yes"]:
        return True
    else:
        return False


def isLink(string):
    """
    Check if string is a hyperlink

    Args:
        string (str): The string to be checked.

    Returns:
        bool
    """
    if findURLs(string) is not []:
        return False  # True
    else:
        return False

# download functions


def findURLs(string):
    """
    Returns all hyperlinks in string in a list

    Args:
        string (str): The string to be checked.

    Returns:
        list with all hyperlinks in string
    """
    # findall() has been used
    # with valid conditions for urls in string
    url = re.findall(
        'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)
    return url


def is_downloadable(url):
    """
    Check if url is downloadable

    Args:
        url (str): The url to be checked.

    Returns:
        bool
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
    """
    Returns the filename from an URL

    Args:
        url (str): The url with filename at the end.

    Returns:
        The filename from an URL
    """
    try:
        remotefile = urlopen(url)
        blah = remotefile.info()['Content-Disposition']
        value, params = cgi.parse_header(blah)
        filename = params["filename"]
        return filename
    except Exception:
        a = urlparse(url)
        return os.path.basename(a.path)


def downloadFile(self, link, newDir):
    """
    DEPRECATED
    Download a file from 'link' to local disk

    Args:
        link (str): The url to download.
        newDir (str): The path, where downloaded files will be stored.

    Returns:
        Unknown
    """
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
    """
    Copy a file from one place to another

    Args:
        origFile (str): The original filepath.
        newDir (str): The path where to file is copied to.

    Returns:
        The new filepath
    """
    filename = os.path.basename(origFile)
    if os.path.join(newDir, filename) is not origFile:
        copy(origFile, newDir)
    return os.path.join(newDir, filename)


def openFile(filepath):
    """
    Open a file with the default system program

    Args:
        filepath (str): The filepath of the file you want to open.

    Returns:
        True if file could be opened
        False if file could not be opened
    """
    logging.info("Opening file: "+filepath)
    try:
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name is 'nt':
            os.startfile(filepath)
        elif os.name is 'posix':
            subprocess.call(('xdg-open', filepath))
        return True
    except Exception:
        logging.warning("Der angegebenen Datei ist keine Anwendung zugeordnet: "+filepath)
        return False

# List functions


def list_duplicates(seq):
    """
    Returns a tuple with all duplicate items in list

    Args:
        seq (list): The list you want to check for duplicates.

    Returns:
        A tuple with all duplicate items in list
    """
    tally = defaultdict(list)
    for i, item in enumerate(seq):
        tally[item].append(i)
    return ((key, locs) for key, locs in tally.items()
            if len(locs) > 1)


def column(matrix, i):
    """
    Get the column i of a nested 2D-list.

    Args:
        matrix (list): A list containing lists: [[i1_1,i1_2...],[i2_1,i2_2...]...].
        i (int): The index of an element in the inner list.

    Returns:
        A list of the i-th element of the inner lists
    """
    ans = []
    for row in matrix:
        if i < len(row):
            ans.append(row[i])
    return ans
#    return [row[i] for row in matrix]
