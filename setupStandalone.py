# windows: python3 setupStandalone.py bdist_msi

from cx_Freeze import setup, Executable
import os
import sys

os.environ['TCL_LIBRARY'] = r'C:\Users\hasch\AppData\Local\Programs\Python\Python36\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\hasch\AppData\Local\Programs\Python\Python36\tcl\tk8.6'
pluginimports = ["requests","socket","minimalmodbus", "serial"]
buildOptions = dict(packages = ["nmap","telegram", "telegram.ext", "matplotlib", "getopt", "numpy","scipy","sys","os","time", "traceback", "multiprocessing", "json", "csv", "xlsxwriter", "importlib", "threading", "collections", "functools", "math", "random", "PyQt5", "pyqtgraph", 'lxml._elementpath','lxml.etree',"markdown2", "idna.idnadata", "idna"]+pluginimports, excludes = ["scipy.spatial.cKDTree"], includes = ["RTOC/","RTOC/LoggerPlugin", "RTOC/data.scriptLibrary"], include_files = ["RTOC/", "RTOC/data/","RTOC/data/icon.png","example_scripts/","RTOC/plugins/","avbin64.dll","README.md","LICENSE", r"C:\Users\hasch\AppData\Local\Programs\Python\Python36\DLLs\tcl86t.dll",
                 r"C:\Users\hasch\AppData\Local\Programs\Python\Python36\DLLs\tk86t.dll"])

base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('RTOC/RTOC.py', base=base)#, icon="data/icon.png",shortcutName="RealTimeOpenControl",shortcutDir="MyProgramMenu")
]

setup(
    name='RealTimeOpenControl',
    version = '1.8.9',
    description = 'RTOC',
    options = dict(build_exe = buildOptions),
    executables = executables
)
