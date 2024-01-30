'''
Provides the bootstrap functions to be invoked on Python interpreter
startup to load supermeter on interpreter startup. This module is invoked from
a '.pth' file.
'''
import sys
import os
import site

try:
    import __builtin__
    _builtin = __builtin__
except ImportError:  # python 3
    import importlib
    _builtin = importlib

# mark if we already bootstrapped supermeter.
_bootstrapped = False
# original __import__ function
_original_import = None
# if we can't restore the original __import__ because someone else already replaced it, we set this to True
_import_hook_passthrough = False

_debug = os.getenv("SUPERTENANT_SUPERMETER_AUTOWRAPT_DEBUG", "false").lower() in ("1", "true", "t", "y", "yes")
def _log(msg):
    sys.stderr.write("[supertenant-supermeter-autowrapt] DEBUG: %s\n" % msg)

if _debug:
    _log("bootstrap loaded")

def can_bootstrap():
    # a lot of modules depend on having sys.argv available, so we can't
    # bootstrap until it's available by python.
    # in cpython's initialization order, this comes before running the
    # main script or module.
    return hasattr(sys, "argv")


def _import_hook(*args, **kwargs):
    global _original_import, _import_hook_passthrough
    if _debug:
        _log("_import_hook: %s" % (args[0],))
    if not _import_hook_passthrough and can_bootstrap():
        if _builtin.__import__ == _import_hook:
            _builtin.__import__ = _original_import
            if _debug:
                _log("_import_hook: removing hook")
        else:  # someone else has already replaced the import hook, so we can't remove outselves.
            if _debug:
                _log("_import_hook: setting passthrough mode")
            _import_hook_passthrough = True
        bootstrap_supermeter()
    return _original_import(*args, **kwargs)


def maybe_bootstrap_supermeter():
    if can_bootstrap():
        bootstrap_supermeter()
        return
    # If we can't bootstrap now, we're still too early in the python interpreter
    # initialization sequence. Since we're past sitecustomize or usercustomize,
    # we have no other good place to hook into, so our best option is to hook
    # into __import__ and check when it's safe to bootstrap.
    # Since the python interpreter "imports" the module or script it executes,
    # we should get called before.
    global _original_import
    if _original_import is None:
        _original_import = _builtin.__import__
        _builtin.__import__ = _import_hook


def bootstrap_supermeter():
    '''Discover and register all post import hooks named in the
    'AUTOWRAPT_BOOTSTRAP' environment variable or if SUPERMETER_BOOTSTRAP. The value of the
    environment variable must be a comma separated list.
    '''

    # This can be called twice if '.pth' file bootstrapping works and
    # the 'autowrapt' wrapper script is still also used. We therefore
    # protect ourselves just in case it is called a second time as we
    # only want to force registration once.

    global _builtin, _bootstrapped
    if _bootstrapped:
        return 

    _bootstrapped = True

    if _debug:
        _log("bootstrap_supermeter")

    # It should be safe to import wrapt at this point as this code will
    # be executed after all Python module search directories have been
    # added to the module search path.

    load_supermeter = False
    if "supermeter" in set(os.environ.get("AUTOWRAPT_BOOTSTRAP", "").split(",")):
        load_supermeter = True
    if os.environ.get("SUPERMETER_BOOTSTRAP", "false").lower() in ("1", "true", "t", "y", "yes"):
        load_supermeter = True

    if load_supermeter:
        if _debug:
            _log("bootstrap_supermeter import and run")
        try:
            supertenant = _builtin.__import__("supertenant.supermeter")
            supertenant.supermeter._load()
        except Exception as e:
            sys.stderr.write("[supertenant-supermeter] FATAL: failed to auto-load, instrumentation will not be available.\n")
            import traceback
            traceback.print_exc()
    else:
        if _debug:
            _log("bootstrap_supermeter NOT import and run")

def _execsitecustomize_wrapper(wrapped):
    def _execsitecustomize(*args, **kwargs):
        try:
            return wrapped(*args, **kwargs)
        finally:
            # Check whether 'usercustomize' module support is disabled.
            # In the case of 'usercustomize' module support being
            # disabled we must instead do our work here after the
            # 'sitecustomize' module has been loaded.
            if not site.ENABLE_USER_SITE:
                maybe_bootstrap_supermeter()

    return _execsitecustomize


def _execusercustomize_wrapper(wrapped):
    def _execusercustomize(*args, **kwargs):
        try:
            return wrapped(*args, **kwargs)
        finally:
            maybe_bootstrap_supermeter()

    return _execusercustomize


_patched = False

def bootstrap():
    '''
    Patches the 'site' module such that the bootstrap function is
    called as the last thing done when initialising the Python interpreter.
    This function would normally be called from the special '.pth' file.
    '''
    global _patched

    if _patched:
        return

    _patched = True

    # We want to do our real work as the very last thing in the 'site'
    # module when it is being imported so that the module search path is
    # initialised properly. What is the last thing executed depends on
    # whether the 'usercustomize' module support is enabled. Support for
    # the 'usercustomize' module will not be enabled in Python virtual
    # enviromments. We therefore wrap the functions for the loading of
    # both the 'sitecustomize' and 'usercustomize' modules but detect
    # when 'usercustomize' support is disabled and in that case do what
    # we need to after the 'sitecustomize' module is loaded.
    #
    # In wrapping these functions though, we can't actually use wrapt to
    # do so. This is because depending on how wrapt was installed it may
    # technically be dependent on '.pth' evaluation for Python to know
    # where to import it from. The addition of the directory which
    # contains wrapt may not yet have been done. We thus use a simple
    # function wrapper instead.

    # If sitecustomize or usercustomize were already executed, then the
    # wrappers below will not be called, so we need to call 
    # maybe_bootstrap_supermeter() immediately.
    if "sitecustomize" in sys.modules or "usercustomize" in sys.modules:
        maybe_bootstrap_supermeter()
        return

    site.execsitecustomize = _execsitecustomize_wrapper(site.execsitecustomize)
    site.execusercustomize = _execusercustomize_wrapper(site.execusercustomize)
