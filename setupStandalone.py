# windows: python3 setupStandalone.py bdist_msi
# IEXPRESS /N D:\Benutzer\haschtl\Dokumente\GIT\kellerlogger\build\RTOC_v2.SED


from cx_Freeze import setup, Executable
import os
import sys

os.environ['TCL_LIBRARY'] = r'C:\Users\hasch\AppData\Local\Programs\Python\Python36\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\hasch\AppData\Local\Programs\Python\Python36\tcl\tk8.6'
pluginimports = ["requests","socket","minimalmodbus", "serial"]
buildOptions = dict(packages = ["nmap","telegram", "telegram.ext", "matplotlib", "websocket_client", "getopt", "numpy","scipy","sys","pandas","os","time", "traceback", "multiprocessing", "json", "csv", "xlsxwriter", "ezodf","importlib", "threading", "collections", "functools", "math", "random", "PyQt5", "pyqtgraph", 'lxml._elementpath','lxml.etree', 'whaaaaat', "markdown2", 'Cryptodome',"github", "idna.idnadata", "idna",'dash_table','dash','gevent', 'plotly','dash_daq','flask', 'statsmodels', 'scikit-learn', 'scikit-metrics', 'patsy']+pluginimports, excludes = ["scipy.spatial.cKDTree"], includes = ["RTOC/","RTOC/LoggerPlugin", "RTOC/RTLogger/scriptLibrary"], include_files = ["RTOC/", "RTOC/data/","RTOC/data/icon.png","example_scripts/","RTOC/RTLogger/plugins/","RTOC/RTLogger/","RTOC/RTOC_GUI/", "avbin64.dll","README.md","LICENSE", r"C:\Users\hasch\AppData\Local\Programs\Python\Python36\DLLs\tcl86t.dll",
                 r"C:\Users\hasch\AppData\Local\Programs\Python\Python36\DLLs\tk86t.dll"])

base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('RTOC.py', base=None) # base)#, icon="data/icon.png",shortcutName="RealTimeOpenControl",shortcutDir="MyProgramMenu")
]

setup(
    name='RealTimeOpenControl',
    version = '3.0',
    description = 'RTOC',
    options = dict(build_exe = buildOptions),
    executables = executables
)
