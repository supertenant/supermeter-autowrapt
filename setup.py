import os

from setuptools import setup

# In newer debian-based systems, there's a dist-packages directory
# where packages may get installed, depending on how the user installs the package -
# for system python (which can be python used by the container) packages are installed
# under dist-packages and for user packages they get installed under site-packages.
# All in all, very confusing and no clear way to tell which one is used.
# Since installing in the wrong place may mean we won't autoload, we want to install
# anywhere we think is relevant.
# In the .pth file we have a safety mechanism to check that the supermeter-autowrapt module
# can be imported - this mechanism won't work for frozen packages though.
def get_lib_dirs():
    import sysconfig
    dirs = set()
    for scheme in sysconfig.get_scheme_names():
        purelib = sysconfig.get_path('purelib', scheme=scheme)
        if os.path.exists(purelib):
            datalib = sysconfig.get_path('data', scheme=scheme)
            if datalib and purelib.startswith(datalib):
                dirs.add(purelib[len(datalib) + 1:])
    try:
        from distutils.sysconfig import get_python_lib
        dirs.add(get_python_lib(prefix=''))
    except ImportError:
        pass
    return dirs


def load_readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.rst'), "rt") as f:
        return f.read()


setup_kwargs = dict(
    name = 'supermeter-autowrapt',
    version = '1.1.10',
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
    long_description=load_readme(),
    long_description_content_type='text/markdown',
    platforms=['any']
)

setup(**setup_kwargs)
