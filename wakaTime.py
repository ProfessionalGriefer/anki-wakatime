# -*- coding: utf-8 -*-
""" ==========================================================
File:        WakaTime.py
Description: Automatic time tracking for Anki
Maintainer:  Vincent Nahn
License:     BSD 3, see LICENSE for more details.
Website:     https://github.com/ProfessionalGriefer/anki-wakatime
==========================================================="""


__version__ = '0.1'

from enum import Enum
import json
import platform
import re
import shutil
import subprocess
import time
import threading
from subprocess import STDOUT, PIPE
from zipfile import ZipFile
from pathlib import Path

import queue

from configparser import ConfigParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# Imports for Anki
# import the main window object (mw) from aqt
from aqt import mw
# import the "show info" tool from utils.py
from aqt.utils import showInfo, qconnect
# import everything from the Qt GUI library
from aqt.qt import *

config = mw.addonManager.getConfig(__name__)


is_win = platform.system() == 'Windows'

class Popen(subprocess.Popen):
    """Patched Popen to prevent opening cmd window on Windows platform."""

    def __init__(self, *args, **kwargs):
        if is_win:
            startupinfo = kwargs.get('startupinfo')
            try:
                startupinfo = startupinfo or subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            except AttributeError:
                pass
            kwargs['startupinfo'] = startupinfo
        super(Popen, self).__init__(*args, **kwargs)


# globals
HOME_FOLDER: Path = Path(os.environ.get('WAKATIME_HOME')).resolve() or Path.home()

RESOURCES_FOLDER            = HOME_FOLDER / '.wakatime'
CONFIG_FILE                 = HOME_FOLDER / '.wakatime.cfg'
INTERNAL_CONFIG_FILE        = HOME_FOLDER / '.wakatime-internal.cfg'
GITHUB_RELEASES_STABLE_URL  = 'https://api.github.com/repos/wakatime/wakatime-cli/releases/latest'
GITHUB_DOWNLOAD_PREFIX      = 'https://github.com/wakatime/wakatime-cli/releases/download'
SETTINGS_FILE               = 'WakaTime.sublime-settings'

SETTINGS = {}
LAST_HEARTBEAT = {
    'time': 0,
    'file': None,
    'is_write': False,
}

LAST_HEARTBEAT_SENT_AT          = 0
LAST_FETCH_TODAY_CODING_TIME    = 0
FETCH_TODAY_DEBOUNCE_COUNTER    = 0
FETCH_TODAY_DEBOUNCE_SECONDS    = 60
LATEST_CLI_VERSION              = None
WAKATIME_CLI_LOCATION: Path | None      = None
HEARTBEATS                      = queue.Queue()
HEARTBEAT_FREQUENCY             = 2     # minutes between logging heartbeat when editing same file
SEND_BUFFER_SECONDS             = 30    # seconds between sending buffered heartbeats to API


# Log Levels
class LogLevel(Enum):
    DEBUG   = 'DEBUG'
    INFO    = 'INFO'
    WARNING = 'WARNING'
    ERROR   = 'ERROR'

def parseConfigFile(configFile: Path):
    """
    Returns a configparser.SafeConfigParser instance with configs
    read from the config file. Default location of the config file is
    at ~/.wakatime.cfg.
    :param configFile: Path
    :return:
    """

    kwargs = {'strict': False}
    configs = ConfigParser(**kwargs)
    try:
        with open(configFile, 'r', encoding='utf-8') as fh:
            try:
                configs.read_file(fh)
                return configs
            except:
                log(LogLevel.ERROR, traceback.format_exc())
                return None
    except IOError:
        log(LogLevel.DEBUG, "Error: Could not read from config file {0}\n".format(configFile))
        return configs

def prompt_api_key() -> str | None:
    """
    Used within the ApiKey class to get the API key from the user if none has been found in the config
    :return: API key
    """
    key, ok = QInputDialog.getText(mw, "Enter the WakaTime API Key", "waka_XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX")

    if ok and key:
        # Save the text to addon's config
        config["wakaTime-api-key"] = key
        mw.addonManager.writeConfig(__name__, config)

        # Optionally show a message confirming it was saved
        showInfo("Your new API key has been saved")

        return key

    return None


class ApiKey(object):
    _key = None

    def read(self):
        if self._key:
            return self._key

        # Read from the Anki Addon Config
        key: str | None = config['wakaTime-api-key']
        if key:
            self._key = key
            return self._key

        # Else prompt for the API Key
        key = prompt_api_key()
        if key:
            self._key = key
            return key


APIKEY = ApiKey()


def set_timeout(callback, seconds):
    """Runs the callback after the given seconds delay.

    If this is Sublime Text 3, runs the callback on an alternate thread.
    """

    milliseconds = int(seconds * 1000)
    sublime.set_timeout_async(callback, milliseconds)


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
        if lvl == LogLevel.DEBUG and not SETTINGS.get('debug'):
            return
        msg = message
        if len(args) > 0:
            msg = message.format(*args)
        elif len(kwargs) > 0:
            msg = message.format(**kwargs)
        print('[WakaTime] [{lvl}] {msg}'.format(lvl=lvl, msg=msg))
    except RuntimeError:
        set_timeout(lambda: log(lvl, message, *args, **kwargs), 0)



def obfuscate_apikey(command_list):
    cmd = list(command_list)
    apikey_index = None
    for num in range(len(cmd)):
        if cmd[num] == '--key':
            apikey_index = num + 1
            break
    if apikey_index is not None and apikey_index < len(cmd):
        cmd[apikey_index] = 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXX' + cmd[apikey_index][-4:]
    return cmd


def enough_time_passed(now, is_write):
    if now - LAST_HEARTBEAT['time'] > HEARTBEAT_FREQUENCY * 60:
        return True
    if is_write and now - LAST_HEARTBEAT['time'] > 2:
        return True
    return False


def find_folder_containing_file(folders, current_file):
    """Returns absolute path to folder containing the file.
    """

    parent_folder = None

    current_folder = current_file
    while True:
        for folder in folders:
            if os.path.realpath(os.path.dirname(current_folder)) == os.path.realpath(folder):
                parent_folder = folder
                break
        if parent_folder is not None:
            break
        if not current_folder or os.path.dirname(current_folder) == current_folder:
            break
        current_folder = os.path.dirname(current_folder)

    return parent_folder


def find_project_from_folders(folders, current_file):
    """Find project name from open folders.
    """

    folder = find_folder_containing_file(folders, current_file)
    return os.path.basename(folder) if folder else None



def handle_activity(view, is_write=False):
    window = view.window()
    if window is not None:
        entity = view.file_name()
        if entity:
            timestamp = time.time()
            last_file = LAST_HEARTBEAT['file']
            if entity != last_file or enough_time_passed(timestamp, is_write):
                project = window.project_data() if hasattr(window, 'project_data') else None
                folders = window.folders()
                append_heartbeat(entity, timestamp, is_write, view, project, folders)


def append_heartbeat(entity, timestamp, is_write, view, project, folders):
    global LAST_HEARTBEAT

    # add this heartbeat to queue
    heartbeat = {
        'entity': entity,
        'timestamp': timestamp,
        'is_write': is_write,
        'project': project,
        'folders': folders,
        'lines_in_file': view.rowcol(view.size())[0] + 1,
    }
    selections = view.sel()
    if selections and len(selections) > 0:
        rowcol = view.rowcol(selections[0].begin())
        row, col = rowcol[0] + 1, rowcol[1] + 1
        heartbeat['lineno'] = row
        heartbeat['cursorpos'] = col
    HEARTBEATS.put_nowait(heartbeat)

    # make this heartbeat the LAST_HEARTBEAT
    LAST_HEARTBEAT = {
        'file': entity,
        'time': timestamp,
        'is_write': is_write,
    }

    # process the queue of heartbeats in the future
    set_timeout(lambda: process_queue(timestamp), SEND_BUFFER_SECONDS)


def process_queue(timestamp):
    global LAST_HEARTBEAT_SENT_AT

    if not isCliInstalled():
        return

    # Prevent sending heartbeats more often than SEND_BUFFER_SECONDS
    now = int(time.time())
    if timestamp != LAST_HEARTBEAT['time'] and LAST_HEARTBEAT_SENT_AT > now - SEND_BUFFER_SECONDS:
        return
    LAST_HEARTBEAT_SENT_AT = now

    try:
        heartbeat = HEARTBEATS.get_nowait()
    except queue.Empty:
        return

    has_extra_heartbeats = False
    extra_heartbeats = []
    try:
        while True:
            extra_heartbeats.append(HEARTBEATS.get_nowait())
            has_extra_heartbeats = True
    except queue.Empty:
        pass

    thread = SendHeartbeatsThread(heartbeat)
    if has_extra_heartbeats:
        thread.add_extra_heartbeats(extra_heartbeats)
    thread.start()


class SendHeartbeatsThread(threading.Thread):
    """Non-blocking thread for sending heartbeats to api.
    """

    def __init__(self, heartbeat):
        threading.Thread.__init__(self)

        self.debug = SETTINGS.get('debug')
        self.api_key = APIKEY.read() or ''
        self.ignore = SETTINGS.get('ignore', [])
        self.include = SETTINGS.get('include', [])
        self.hideFileNames = SETTINGS.get('hide-file-names')
        self.proxy = SETTINGS.get('proxy')

        self.heartbeat = heartbeat
        self.has_extra_heartbeats = False

    def add_extra_heartbeats(self, extra_heartbeats):
        self.has_extra_heartbeats = True
        self.extra_heartbeats = extra_heartbeats

    def run(self):
        """Running in background thread."""

        self.send_heartbeats()

    def build_heartbeat(
        self,
        entity=None,
        timestamp=None,
        is_write=None,
        lineno=None,
        cursorpos=None,
        lines_in_file=None,
        project=None,
        folders=None
    ):
        """Returns a dict for passing to wakatime-cli as arguments."""

        heartbeat = {
            'entity': entity,
            'timestamp': timestamp,
            'is_write': is_write,
        }

        if project and project.get('name'):
            heartbeat['alternate_project'] = project.get('name')
        elif folders:
            project_name = find_project_from_folders(folders, entity)
            if project_name:
                heartbeat['alternate_project'] = project_name

        if lineno is not None:
            heartbeat['lineno'] = lineno
        if cursorpos is not None:
            heartbeat['cursorpos'] = cursorpos
        if lines_in_file is not None:
            heartbeat['lines-in-file'] = lines_in_file

        return heartbeat

    def send_heartbeats(self):
        heartbeat = self.build_heartbeat(**self.heartbeat)
        ua = 'anki-wakatime/%s' % __version__
        cmd = [
            getCliLocation(),
            '--entity', heartbeat['entity'],
            '--time', str('%f' % heartbeat['timestamp']),
            '--plugin', ua,
        ]
        if self.api_key:
            cmd.extend(['--key', str(bytes.decode(self.api_key.encode('utf8')))])
        if heartbeat['is_write']:
            cmd.append('--write')
        if heartbeat.get('alternate_project'):
            cmd.extend(['--alternate-project', heartbeat['alternate_project']])
        if heartbeat.get('lineno') is not None:
            cmd.extend(['--lineno', '{0}'.format(heartbeat['lineno'])])
        if heartbeat.get('cursorpos') is not None:
            cmd.extend(['--cursorpos', '{0}'.format(heartbeat['cursorpos'])])
        if heartbeat.get('lines_in_file') is not None:
            cmd.extend(['--lines-in-file', '{0}'.format(heartbeat['lines_in_file'])])
        for pattern in self.ignore:
            cmd.extend(['--exclude', pattern])
        for pattern in self.include:
            cmd.extend(['--include', pattern])
        if self.debug:
            cmd.append('--verbose')
        if self.hideFileNames:
            cmd.append('--hide-file-names')
        if self.proxy:
            cmd.extend(['--proxy', self.proxy])
        if self.has_extra_heartbeats:
            cmd.append('--extra-heartbeats')
            stdin = PIPE
            extra_heartbeats = json.dumps([self.build_heartbeat(**x) for x in self.extra_heartbeats])
            inp = "{0}\n".format(extra_heartbeats).encode('utf-8')
        else:
            extra_heartbeats = None
            stdin = None
            inp = None

        log(LogLevel.DEBUG, ' '.join(obfuscate_apikey(cmd)))
        try:
            process = Popen(cmd, stdin=stdin, stdout=PIPE, stderr=STDOUT)
            output, _err = process.communicate(input=inp)
            retcode = process.poll()
            if retcode:
                log(LogLevel.DEBUG if retcode == 102 or retcode == 112 else LogLevel.ERROR, 'wakatime-core exited with status: {0}'.format(retcode))
            if output:
                log(LogLevel.ERROR, 'wakatime-core output: {0}'.format(output))
        except:
            log(LogLevel.ERROR, sys.exc_info()[1])


class WakatimeListener(sublime_plugin.EventListener):

    def on_post_save(self, view):
        handle_activity(view, is_write=True)

    def on_selection_modified(self, view):
        if is_view_active(view):
            handle_activity(view)

    def on_modified(self, view):
        if is_view_active(view):
            handle_activity(view)



class UpdateCLI(threading.Thread):
    """Non-blocking thread for downloading latest wakatime-cli from GitHub.
    """

    def run(self):
        if isCliLatest():
            return

        log(LogLevel.INFO, 'Downloading wakatime-cli...')

        if os.path.isdir(os.path.join(RESOURCES_FOLDER, 'wakatime-cli')):
            shutil.rmtree(os.path.join(RESOURCES_FOLDER, 'wakatime-cli'))

        if not os.path.exists(RESOURCES_FOLDER):
            os.makedirs(RESOURCES_FOLDER)

        try:
            url = cliDownloadUrl()
            log(LogLevel.DEBUG, 'Downloading wakatime-cli from {url}'.format(url=url))
            zip_file = os.path.join(RESOURCES_FOLDER, 'wakatime-cli.zip')
            download(url, zip_file)

            if isCliInstalled():
                try:
                    os.remove(getCliLocation())
                except:
                    log(LogLevel.DEBUG, traceback.format_exc())

            log(LogLevel.INFO, 'Extracting wakatime-cli...')
            with ZipFile(zip_file) as zf:
                zf.extractall(RESOURCES_FOLDER)

            if not is_win:
                os.chmod(getCliLocation(), 509)  # 755

            try:
                os.remove(os.path.join(RESOURCES_FOLDER, 'wakatime-cli.zip'))
            except:
                log(LogLevel.DEBUG, traceback.format_exc())
        except:
            log(LogLevel.DEBUG, traceback.format_exc())

        createSymlink()

        log(LogLevel.INFO, 'Finished extracting wakatime-cli.')


def getCliLocation():
    global WAKATIME_CLI_LOCATION

    if not WAKATIME_CLI_LOCATION:
        binary = 'wakatime-cli-{osname}-{arch}{ext}'.format(
            osname=platform.system().lower(),
            arch=architecture(),
            ext='.exe' if is_win else '',
        )
        WAKATIME_CLI_LOCATION = os.path.join(RESOURCES_FOLDER, binary)

    return WAKATIME_CLI_LOCATION


def architecture():
    arch = platform.machine() or platform.processor()
    if arch == 'armv7l':
        return 'arm'
    if arch == 'aarch64':
        return 'arm64'
    if 'arm' in arch:
        return 'arm64' if sys.maxsize > 2**32 else 'arm'
    return 'amd64' if sys.maxsize > 2**32 else '386'


def isCliInstalled():
    return os.path.exists(getCliLocation())


def isCliLatest():
    if not isCliInstalled():
        return False

    args = [getCliLocation(), '--version']
    try:
        stdout, stderr = Popen(args, stdout=PIPE, stderr=PIPE).communicate()
    except:
        return False
    stdout = (stdout or b'') + (stderr or b'')
    localVer = extractVersion(stdout.decode('utf-8'))
    if not localVer:
        log(LogLevel.DEBUG, 'Local wakatime-cli version not found.')
        return False

    log(LogLevel.INFO, 'Current wakatime-cli version is %s' % localVer)
    log(LogLevel.INFO, 'Checking for updates to wakatime-cli...')

    remoteVer = getLatestCliVersion()

    if not remoteVer:
        return True

    if remoteVer == localVer:
        log(LogLevel.INFO, 'wakatime-cli is up to date.')
        return True

    log(LogLevel.INFO, 'Found an updated wakatime-cli %s' % remoteVer)
    return False


def getLatestCliVersion():
    global LATEST_CLI_VERSION

    if LATEST_CLI_VERSION:
        return LATEST_CLI_VERSION

    configs, last_modified, last_version = None, None, None
    try:
        configs = parseConfigFile(INTERNAL_CONFIG_FILE)
        if configs:
            last_modified, last_version = lastModifiedAndVersion(configs)
    except:
        log(LogLevel.DEBUG, traceback.format_exc())

    try:
        headers, contents, code = request(GITHUB_RELEASES_STABLE_URL, last_modified=last_modified)

        log(LogLevel.DEBUG, 'GitHub API Response {0}'.format(code))

        if code == 304:
            LATEST_CLI_VERSION = last_version
            return last_version

        data = json.loads(contents.decode('utf-8'))

        ver = data['tag_name']
        log(LogLevel.DEBUG, 'Latest wakatime-cli version from GitHub: {0}'.format(ver))

        if configs:
            last_modified = headers.get('Last-Modified')
            if not configs.has_section('internal'):
                configs.add_section('internal')
            configs.set('internal', 'cli_version', ver)
            configs.set('internal', 'cli_version_last_modified', last_modified)
            with open(INTERNAL_CONFIG_FILE, 'w', encoding='utf-8') as fh:
                configs.write(fh)

        LATEST_CLI_VERSION = ver
        return ver
    except:
        log(LogLevel.DEBUG, traceback.format_exc())
        return None


def lastModifiedAndVersion(configs):
    last_modified, last_version = None, None
    if configs.has_option('internal', 'cli_version'):
        last_version = configs.get('internal', 'cli_version')
    if last_version and configs.has_option('internal', 'cli_version_last_modified'):
        last_modified = configs.get('internal', 'cli_version_last_modified')
    if last_modified and last_version and extractVersion(last_version):
        return last_modified, last_version
    return None, None


def extractVersion(text):
    pattern = re.compile(r"([0-9]+\.[0-9]+\.[0-9]+)")
    match = pattern.search(text)
    if match:
        return 'v{ver}'.format(ver=match.group(1))
    return None


def cliDownloadUrl():
    osname = platform.system().lower()
    arch = architecture()

    validCombinations = [
      'darwin-amd64',
      'darwin-arm64',
      'freebsd-386',
      'freebsd-amd64',
      'freebsd-arm',
      'linux-386',
      'linux-amd64',
      'linux-arm',
      'linux-arm64',
      'netbsd-386',
      'netbsd-amd64',
      'netbsd-arm',
      'openbsd-386',
      'openbsd-amd64',
      'openbsd-arm',
      'openbsd-arm64',
      'windows-386',
      'windows-amd64',
      'windows-arm64',
    ]
    check = '{osname}-{arch}'.format(osname=osname, arch=arch)
    if check not in validCombinations:
        reportMissingPlatformSupport(osname, arch)

    version = getLatestCliVersion()

    return '{prefix}/{version}/wakatime-cli-{osname}-{arch}.zip'.format(
        prefix=GITHUB_DOWNLOAD_PREFIX,
        version=version,
        osname=osname,
        arch=arch,
    )


def reportMissingPlatformSupport(osname, arch):
    url = 'https://api.wakatime.com/api/v1/cli-missing?osname={osname}&architecture={arch}&plugin=anki'.format(
        osname=osname,
        arch=arch,
    )
    request(url)


def request(url, last_modified=None):
    req = Request(url)
    req.add_header('User-Agent', 'github.com/wakatime/sublime-wakatime')

    proxy = SETTINGS.get('proxy')
    if proxy:
        req.set_proxy(proxy, 'https')

    if last_modified:
        req.add_header('If-Modified-Since', last_modified)

    try:
        resp = urlopen(req)
        headers = resp.headers
        return headers, resp.read(), resp.getcode()
    except HTTPError as err:
        if err.code == 304:
            return None, None, 304

        log(LogLevel.DEBUG, err.read().decode())
        raise
    except IOError:
        raise


def download(url, filePath):
    req = Request(url)
    # req.add_header('User-Agent', 'github.com/wakatime/anki-wakatime')

    proxy = SETTINGS.get('proxy')
    if proxy:
        req.set_proxy(proxy, 'https')

    with open(filePath, 'wb') as fh:
        try:
            resp = urlopen(req)
            fh.write(resp.read())
        except HTTPError as err:
            if err.code == 304:
                return None, None, 304

            log(LogLevel.DEBUG, err.read().decode())
            raise
        except IOError:

            raise


def is_symlink(path):
    return os.path.islink(path) or False


def createSymlink():
    link: Path = RESOURCES_FOLDER
    if is_win:
        link = link / 'wakatime-cli.exe'
    else:
        link = link / 'wakatime-cli'

    if link.exists() and link.is_symlink():
        return  # don't re-create symlink on Unix-like platforms

    try:
        link.symlink_to(getCliLocation())
    except:
        try:
            shutil.copy2(getCliLocation(), link)
            if not is_win:
                os.chmod(link, 509)  # 755
        except:
            log(LogLevel.WARNING, traceback.format_exc())

