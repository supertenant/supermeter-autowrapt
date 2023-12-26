import os
import sys
import glob
import subprocess
from collections import namedtuple

def fail(result, message):
    print("exit code: %s" % (result.returncode,))
    print("stdout:\n%s\nstderr:\n%s\n" % (result.stdout, result.stderr))
    raise AssertionError(message)


Result = namedtuple("Result", ["returncode", "stdout", "stderr"]
                    )
def run_hello(subdir, import_site=True, env={}):
    here = os.path.dirname(__file__)
    command = [sys.executable]
    if not import_site:
        command.append("-s")
    command.append(os.sep.join([here, "hello.py"]))

    new_python_path = os.pathsep.join([os.sep.join([here, subdir]), os.environ.get("PYTHONPATH", "")])
    base_env = os.environ.copy()
    base_env.update({"PYTHONPATH": new_python_path})
    base_env.update(env)

    # Need to be python 2.7 compatible, so no subprocess.run()...
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=base_env)
    stdout, stderr = process.communicate()
    result = Result(process.returncode, stdout.decode("utf-8"), stderr.decode("utf-8"))
    if result.returncode != 0:
        fail(result, "process returned non-zero exit code")
    return result


def filter_out_debug(s):
    debug_enabled = os.getenv("SUPERTENANT_SUPERMETER_AUTOWRAPT_DEBUG", "false").lower() in ("1", "true", "t", "y", "yes")
    if debug_enabled:
        return "\n".join(n for n in s.split("\n") if not n.startswith("[supertenant-supermeter-autowrapt] DEBUG:"))
    return s


def test_sanity(import_site):
    print("test_sanity import_site=%r" % (import_site,))
    result = run_hello("good_path", import_site=import_site)
    stdout, stderr = result.stdout, result.stderr
    if stdout != "hello world.\n":
        fail(result, "output is not 'hello world.'")
    if stderr != "":
        fail(result, "stderr is not empty")


def test_bootstrap(import_site):
    print("test_bootstrap import_site=%r" % (import_site,))
    envs = [
        {"AUTOWRAPT_BOOTSTRAP": "supermeter"},
        {"AUTOWRAPT_BOOTSTRAP": "a,b,c,supermeter,d,e"},
        {"SUPERMETER_BOOTSTRAP": "1"},
        {"SUPERMETER_BOOTSTRAP": "True"},
        {"SUPERMETER_BOOTSTRAP": "t"},
    ]
    for env in envs:
        result = run_hello("good_path", import_site=import_site, env=env)
        stdout, stderr = result.stdout, result.stderr
        if stdout != "supermeter loaded successfully.\nhello world.\n":
            fail(result, "output doesn't start with 'supermeter loaded successfully.'")
        if filter_out_debug(stderr) != "":
            fail(result, "stderr is not empty")


def test_no_bootstrap(import_site):
    print("test_no_bootstrap import_site=%r" % (import_site,))
    envs = [
        {"AUTOWRAPT_BOOTSTRAP": "supermeterx"},
        {"AUTOWRAPT_BOOTSTRAP": "a,b,c,supermeterx,d,e"},
        {"SUPERMETER_BOOTSTRAP": "0"},
        {"SUPERMETER_BOOTSTRAP": "f"},
        {"SUPERMETER_BOOTSTRAP": "False"},
    ]
    for env in envs:
        result = run_hello("good_path", import_site=import_site, env=env)
        stdout, stderr = result.stdout, result.stderr
        if stdout != "hello world.\n":
            fail(result, "output doesn't start with 'supermeter loaded successfully.'")
        if filter_out_debug(stderr) != "":
            fail(result, "stderr is not empty")


def test_bootstrap_error(import_site):
    print("test_bootstrap_error import_site=%r" % (import_site,))
    envs = [
        {"AUTOWRAPT_BOOTSTRAP": "supermeter"},
        {"AUTOWRAPT_BOOTSTRAP": "a,b,c,supermeter,d,e"},
        {"SUPERMETER_BOOTSTRAP": "1"},
        {"SUPERMETER_BOOTSTRAP": "True"},
        {"SUPERMETER_BOOTSTRAP": "t"},
    ]
    for env in envs:
        result = run_hello("bad_path", import_site=import_site, env=env)
        stdout, stderr = result.stdout, result.stderr
        if stdout != "hello world.\n":
            fail(result, "output isn't hello world.")
        if not filter_out_debug(stderr).startswith("[supertenant-supermeter] FATAL: failed to auto-load, instrumentation will not be available"):
            fail(result, "stderr doesn't start with expected error message")


def build_and_install():
    here = os.path.dirname(__file__)
    root = os.path.abspath(os.sep.join([here, ".."]))
    try:
        print("building sdist package.")
        # python 3.12 doesn't come w/ setuptools, so we need to install it, but we want to remove it so there won't
        # be other side effects when running.
        remove_setuptools = False
        try:
            import setuptools
        except ImportError:
            print("setuptools not available, installing.")
            subprocess.check_output(
                [sys.executable, "-m", "pip", "install", "setuptools"], stderr=subprocess.STDOUT
            )
            remove_setuptools = True

        subprocess.check_output([sys.executable, "setup.py", "sdist"], cwd=root, stderr=subprocess.STDOUT)
        if remove_setuptools:
            print("uninstalling setuptools.")
            uninstall("setuptools")
        # we deliberately don't use --find-links or just the package name when installing so there's no chance
        # pip will grab it from pypi.
        sdists = glob.glob(os.path.sep.join([root, "dist", "supermeter-autowrapt-*.tar.gz"]))
        if len(sdists) != 1:
            raise AssertionError("expected one sdist, got %s" % (sdists,))

        print("installing sdist package.")
        subprocess.check_output(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", sdists[0]], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        print("exit code: %s" % (e.returncode,))
        print("stdout:\n%s\nstderr:\n%s\n" % (e.stdout, e.stderr))
        raise

def uninstall(name):
    try:
        subprocess.check_output([
            sys.executable, "-m", "pip", "uninstall", "-y", name
        ], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print("exit code: %s" % (e.returncode,))
        print("stdout:\n%s\nstderr:\n%s\n" % (e.stdout, e.stderr))
        raise


if __name__ == "__main__":
    try:
        build_and_install()
        for import_site in [True, False]:
            test_sanity(import_site)
            test_bootstrap(import_site)
            test_no_bootstrap(import_site)
            test_bootstrap_error(import_site)
    finally:
        uninstall("supermeter-autowrapt")