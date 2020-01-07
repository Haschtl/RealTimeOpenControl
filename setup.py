# Tutorial at https://blog.jetbrains.com/pycharm/2017/05/how-to-publish-your-package-on-pypi/
# https://packaging.python.org/tutorials/packaging-projects/

# python3 setup.py sdist bdist_wheel
# python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
# python.exe -m pip install --index-url https://test.pypi.org/simple/ RTOC

# virtual env for testing:
# > virtualenv <DIR>
# move to directory and use python from There

# public:
# python3 setup.py bdist_wheel
# python3 -m twine upload dist\*


# select different dependencie-levels:
# pip install 'RTOC'
# pip install 'RTOC[Telegram]'
# pip install 'RTOC[GUI]'
# pip install 'RTOC[ALL]'

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setupOpts = dict(
    name='RTOC',
    description='RealTime OpenControl',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='GNU',
    url='https://github.com/Haschtl/RealTimeOpenControl',
    author='Sebastian Keller',
    author_email='sebastiankeller@online.de',
    classifiers=[
        # "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        # "Development Status :: 2.3",
        "Environment :: Other Environment",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Software Development :: User Interfaces",
    ],
)


import distutils.dir_util
from distutils.command import build
import os
import sys
import re
try:
    import setuptools
    from setuptools import setup
    from setuptools.command import install
except (ImportError, SystemError):
    sys.stderr.write("Warning: could not import setuptools; falling back to distutils.\n")
    from distutils.core import setup
    from distutils.command import install


# Work around mbcs bug in distutils.
# http://bugs.python.org/issue10945
import codecs
try:
    codecs.lookup('mbcs')
except LookupError:
    ascii = codecs.lookup('ascii')
    func = lambda name, enc=ascii: {True: enc}.get(name == 'mbcs')
    codecs.register(func)


path = os.path.split(__file__)[0]
# sys.path.insert(0, os.path.join(path, 'tools'))

version = "3.0"
forcedVersion = "3.0"
gitVersion = "3.0"
initVersion = 1.0


class Build(build.build):
    """
    * Clear build path before building
    """

    def run(self):
        global path

        # Make sure build directory is clean
        buildPath = os.path.join(path, self.build_lib)
        if os.path.isdir(buildPath):
            distutils.dir_util.remove_tree(buildPath)

        ret = build.build.run(self)
        return ret


class Install(install.install):
    """
    * Check for previously-installed version before installing
    * Set version string in __init__ after building. This helps to ensure that we
      know when an installation came from a non-release code base.
    """

    def run(self):
        global path, version, initVersion, forcedVersion, installVersion

        name = self.config_vars['dist_name']
        path = os.path.join(self.install_libbase, 'RTOC')
        if os.path.exists(path):
            raise Exception("It appears another version of %s is already "
                            "installed at %s; remove this before installing."
                            % (name, path))
        print("Installing to %s" % path)
        rval = install.install.run(self)

        # If the version in __init__ is different from the automatically-generated
        # version string, then we will update __init__ in the install directory
        if initVersion == version:
            return rval

        try:
            initfile = os.path.join(path, '__init__.py')
            data = open(initfile, 'r').read()
            open(initfile, 'w').write(re.sub(r"__version__ = .*", "__version__ = '%s'" % version, data))
            installVersion = version
        except Exception:
            sys.stderr.write("Warning: Error occurred while setting version string in build path. "
                             "Installation will use the original version string "
                             "%s instead.\n" % (initVersion)
                             )
            if forcedVersion:
                raise
            installVersion = initVersion
            sys.excepthook(*sys.exc_info())

        return rval


setup(
    version=version,
    entry_points={
        'console_scripts': [
            'RTOC = RTOC:main',
        ],
    },
    packages=setuptools.find_packages(),
    # package_dir={'RTOC': 'RTOC', 'RTOC.plugins':'plugins', 'RTOC.example_scripts':'example_scripts'},  ## install examples along with the rest of the source
    package_data={
        'RTOC': ['*'],
        # 'RTOC': ['*']
    },
    python_requires='>=3',
    include_package_data=True,
    install_requires=[
        'numpy',
        'requests',
        # 'scipy',
        # 'pyqt5',
        # 'pyqtgraph',
        # 'markdown2',
        # 'xlsxwriter',
        #        'QDarkStyle',
        #        'qtmodern',
        #        'qdarkgraystyle',
        # 'python-telegram-bot',
        # 'matplotlib',
        'python-nmap',
        'whaaaaat',
        'prompt_toolkit',
        # 'dash',
        'pycryptodomex',
        # 'pyGithub',
        # 'pandas',
        # 'ezodf',
        # websocket-server,
		'websocket_client'
    ],
    extras_require={
        'GUI':  ["pyqt5", "pyqtgraph", "markdown2", "pyGithub", "pandas", "scipy", "ezodf", "xlsxwriter"],
        'Telegram': ["matplotlib", "python-telegram-bot", ],
        'ALL': ["pyqt5", "pyqtgraph", "markdown2", "pyGithub", "pandas", "scipy", "ezodf", "xlsxwriter", "matplotlib", "python-telegram-bot", 'dash_table', 'statsmodels', 'scikit-learn', 'scikit-metrics', 'patsy','psycopg2']
    },
    **setupOpts
)
