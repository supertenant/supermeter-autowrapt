import sys
import os

from setuptools import setup

# In newer debian-based systems, there's a dist-packages directory
# where user packages get installed (and not site-packages), so we
# want to put out .pth file there as well.
def get_lib_dirs():
    dirs = []
    try:
        from distutils.sysconfig import get_python_lib
        dirs.append(get_python_lib(prefix=''))
    except ImportError:
        pass
    import sysconfig
    purelib = sysconfig.get_paths().get('purelib', '')
    datalib = sysconfig.get_paths().get('data', '')
    if purelib and datalib and purelib.startswith(datalib):
        dirs.append(purelib[len(datalib) + 1:])
    return dirs


setup_kwargs = dict(
    name = 'supermeter-autowrapt',
    version = '1.1.6',
    description = 'Boostrap mechanism for monkey patches for supermeter.',
    author = 'SuperTenant Ltd.',
    author_email = 'info@supertenant.com',
    license = 'BSD',
    url = 'https://github.com/supertenant/supermeter-autowrapt',
    packages = ['supermeter-autowrapt'],
    package_dir = {'supermeter-autowrapt': 'src'},
    package_data = {},
    data_files = [(d, ['supermeter-init.pth']) for d in get_lib_dirs()],
    entry_points = {},
    install_requires = ['wrapt>=1.10.4'],
)

setup(**setup_kwargs)
