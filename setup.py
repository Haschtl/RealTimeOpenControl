# Tutorial at https://blog.jetbrains.com/pycharm/2017/05/how-to-publish-your-package-on-pypi/
# https://packaging.python.org/tutorials/packaging-projects/

# python setup.py sdist bdist_wheel
# python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
# python.exe -m pip install --index-url https://test.pypi.org/simple/ RTOC

# virtual env for testing:
#> virtualenv <DIR>
# move to directory and use python from There

# public:
# python setup.py bdist_wheel

DESCRIPTION = """\
RealTime OpenControl is a universal measurement, plot and control-software.
It's purpose is to put measurements from different devices (for example 3d-printers, multimeters, power supplies, microcontroller,...) into one tool.
Its fully expandable for every device with Python-Plugins and a running TCP-server.
You can also control the devices (if your plugin has this functionality) with python-scripts, which you can write and run at runtime! This makes it also possible to plot everything else.
There are some example-plugins and example-scripts included.
It also offers an extended plotting-GUI with multiple plots, measure-tools, style-adjustments.
"""

setupOpts = dict(
    name='RTOC',
    description='RealTime OpenControl',
    long_description=DESCRIPTION,
    license='GNU',
    url='https://github.com/Haschtl/RealTimeOpenControl',
    author='Sebastian Keller',
    author_email='sebastiankeller@online.de',
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        #"Development Status :: 2.3",
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
import os, sys, re
try:
    import setuptools
    from setuptools import setup
    from setuptools.command import install
except ImportError:
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
    func = lambda name, enc=ascii: {True: enc}.get(name=='mbcs')
    codecs.register(func)


path = os.path.split(__file__)[0]
#sys.path.insert(0, os.path.join(path, 'tools'))

version = 1.7
forcedVersion = 1.7
gitVersion =1.7
initVersion=1.0



class Build(build.build):
    """
    * Clear build path before building
    """
    def run(self):
        global path

        ## Make sure build directory is clean
        buildPath = os.path.join(path, self.build_lib)
        if os.path.isdir(buildPath):
            distutils.dir_util.remove_tree(buildPath)

        ret = build.build.run(self)


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
        except:
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
    packages=setuptools.find_packages(),
    #package_dir={'RTOC': 'RTOC', 'RTOC.plugins':'plugins', 'RTOC.example_scripts':'example_scripts'},  ## install examples along with the rest of the source
    package_data={
        'RTOC': ['*'],
        'RTOC': ['*']
    },
    python_requires='>=3',
    include_package_data=True,
    install_requires = [
        'numpy',
        'pyqt5',
        'pyqtgraph',
        'markdown2',
        'xlsxwriter',
        'scipy',
        'qtmodern',
        'python-telegram-bot',
        'matplotlib',
        'requests',
        'python-nmap'
        ],
    **setupOpts
)
