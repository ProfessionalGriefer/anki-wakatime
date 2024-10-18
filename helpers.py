"""
Helper functions
"""
from enum import Enum
import subprocess
import threading
from typing import Callable
from pathlib import Path
from configparser import ConfigParser
import traceback

import globals as g


# Log Levels
class LogLevel(Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'


def log(lvl: LogLevel, message, *args, **kwargs):
    """
    Logging messages
    :param lvl:
    :param message:
    :param args:
    :param kwargs:
    :return:
    """
    try:
        if lvl == LogLevel.DEBUG and not g.SETTINGS.get('debug'):
            return
        msg = message
        if len(args) > 0:
            msg = message.format(*args)
        elif len(kwargs) > 0:
            msg = message.format(**kwargs)
        print('[WakaTime] [{lvl}] {msg}'.format(lvl=lvl, msg=msg))

    except RuntimeError:
        set_timeout(lambda: log(lvl, message, *args, **kwargs), 0)


class Popen(subprocess.Popen):
    """Patched Popen to prevent opening cmd window on Windows platform."""

    def __init__(self, *args, **kwargs):
        if g.is_win:
            startupinfo = kwargs.get('startupinfo')
            try:
                startupinfo = startupinfo or subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            except AttributeError:
                pass
            kwargs['startupinfo'] = startupinfo
        super(Popen, self).__init__(*args, **kwargs)


def set_timeout(callback: Callable, seconds: int):
    """
    Executes the callback non-blockingly in a different thread.
    Runs the callback on an alternate thread in the original implementation for Sublime
    """

    # milliseconds = int(seconds * 1000)
    # sublime.set_timeout_async(callback, milliseconds)
    timer = threading.Timer(seconds, callback)
    timer.start()


def obfuscate_apikey(command_list: list[str]):
    """
    Hides the API key when printing the command_list to the console
    :param command_list:
    :return:
    """
    cmd = list(command_list)
    if '--key' not in cmd:
        return cmd
    apikey_index = cmd.index('--key') + 1

    if apikey_index is not None and apikey_index < len(cmd):
        cmd[apikey_index] = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXX' + cmd[apikey_index][-4:]
    return cmd


def parseConfigFile(configFile: Path) -> ConfigParser | None:
    """
    Returns a configparser.SafeConfigParser instance with configs
    read from the config file. Default location of the config file is
    at ~/.wakatime.cfg.
    :param configFile: Path
    :return: ConfigParser object if successful
    """

    kwargs = {'strict': False}
    configs = ConfigParser(**kwargs)
    try:
        with configFile.open(mode='r', encoding='utf-8') as f:
            try:
                configs.read_file(f)
                return configs
            except:
                log(LogLevel.ERROR, traceback.format_exc())
                return None
    except IOError:
        log(LogLevel.DEBUG, f"Error: Could not read from config file {configFile}\n")
        return configs


def enough_time_passed(now: float, is_write: bool) -> bool:
    if now - g.LAST_HEARTBEAT['time'] > g.HEARTBEAT_FREQUENCY * 60:
        return True
    if is_write and now - g.LAST_HEARTBEAT['time'] > 2:
        return True
    return False
