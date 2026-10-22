"""Private, user-owned scratch directories for capture and training tools."""
import os
from pathlib import Path
import stat


def private_dir(path):
    path = Path(path)
    try:
        path.mkdir(mode=0o700, exist_ok=True)
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('not an owned directory (symlinks are refused)')
        path.chmod(0o700)
    except (OSError, ValueError) as error:
        raise SystemExit(f'Unsafe scratch directory {path}: {error}') from error
    return path


def capture_env(home, *, keep_bus=False):
    """Isolate capture state; optionally retain the caller's private session bus."""
    home = private_dir(home)
    env = dict(PATH=os.environ.get('PATH', '/usr/bin:/bin'), LANG='C.UTF-8')
    env['HOME'] = str(home)
    if keep_bus and os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
        env['DBUS_SESSION_BUS_ADDRESS'] = os.environ['DBUS_SESSION_BUS_ADDRESS']
    for key, sub in (('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                     ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state'),
                     ('XDG_RUNTIME_DIR', 'run')):
        env[key] = str(private_dir(home / sub))
    return env
