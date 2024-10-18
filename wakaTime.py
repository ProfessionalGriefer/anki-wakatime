# -*- coding: utf-8 -*-
""" ==========================================================
File:        WakaTime.py
Description: Automatic time tracking for Anki
Maintainer:  Vincent Nahn
License:     BSD 3, see LICENSE for more details.
Website:     https://github.com/ProfessionalGriefer/anki-wakatime
==========================================================="""

__version__ = '0.1'

import json
import time
import threading
from subprocess import STDOUT, PIPE
from queue import Empty as QueueEmpty

# Imports for Anki
from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *
ankiConfig = mw.addonManager.getConfig(__name__)

# Custom imports
from cli import isCliInstalled, getCliLocation
from types import HeartBeatType, LastHeartBeatType
from helpers import LogLevel, log, Popen, obfuscate_apikey, set_timeout
import globals as g

class ApiDialogWidget(QInputDialog):
    """
    Used within the ApiKey class to get the API key from the user if none has been found in the config
    Must be a class because it is displaying a new QtWidget
    :return: API key
    """
    def __init__(self):
        super().__init__()

    def prompt(self) -> str | None:
        promptText = "Enter the WakaTime API Key"
        wakaKeyTemplate = "waka_XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
        key, ok = QInputDialog.getText(self, promptText, wakaKeyTemplate)

        if ok and key:
            # Save the text to addon's config
            ankiConfig["wakaTime-api-key"] = key
            mw.addonManager.writeConfig(__name__, ankiConfig)

            # Optionally show a message confirming it was saved
            showInfo("Your new API key has been saved")

            return key

        return None


class ApiKey(object):
    _key = None

    def read(self) -> str | None:
        if self._key:
            return self._key

        # Read from the Anki Addon Config
        key: str | None = ankiConfig['wakaTime-api-key']
        if key:
            self._key = key
            return self._key

        # Else prompt for the API Key
        dialog = ApiDialogWidget()
        key = dialog.prompt()

        if key:
            self._key = key
            return key
        return None


APIKEY = ApiKey()



def enough_time_passed(now: float, is_write: bool) -> bool:
    if now - g.LAST_HEARTBEAT['time'] > g.HEARTBEAT_FREQUENCY * 60:
        return True
    if is_write and now - g.LAST_HEARTBEAT['time'] > 2:
        return True
    return False


def handle_activity(view, is_write=False):
    window = view.window()
    if window is not None:
        entity = view.file_name()
        if entity:
            timestamp: float = time.time()
            last_file = g.LAST_HEARTBEAT['file']
            if entity != last_file or enough_time_passed(timestamp, is_write):
                project = window.project_data() if hasattr(window, 'project_data') else None
                folders = window.folders()
                append_heartbeat(entity, timestamp, is_write, view, project, folders)


def append_heartbeat(entity, timestamp, is_write, view, project, folders):

    # add this heartbeat to queue
    heartbeat: HeartBeatType = {
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
    g.HEARTBEATS.put_nowait(heartbeat)

    # make this heartbeat the LAST_HEARTBEAT
    g.LAST_HEARTBEAT: LastHeartBeatType = {
        'file': entity,
        'time': timestamp,
        'is_write': is_write,
    }

    # process the queue of heartbeats in the future
    set_timeout(lambda: process_queue(timestamp), g.SEND_BUFFER_SECONDS)


def process_queue(timestamp):

    if not isCliInstalled():
        return

    # Prevent sending heartbeats more often than SEND_BUFFER_SECONDS
    now = int(time.time())
    if timestamp != g.LAST_HEARTBEAT['time'] and g.LAST_HEARTBEAT_SENT_AT > now - g.SEND_BUFFER_SECONDS:
        return
    g.LAST_HEARTBEAT_SENT_AT = now

    try:
        heartbeat = g.HEARTBEATS.get_nowait()
    except QueueEmpty:
        return

    has_extra_heartbeats = False
    extra_heartbeats = []
    try:
        while True:
            extra_heartbeats.append(g.HEARTBEATS.get_nowait())
            has_extra_heartbeats = True
    except QueueEmpty:
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

        self.debug = g.SETTINGS.get('debug')
        self.api_key = APIKEY.read() or ''
        self.ignore = g.SETTINGS.get('ignore', [])
        self.include = g.SETTINGS.get('include', [])
        self.hideFileNames = g.SETTINGS.get('hide-file-names')
        self.proxy = g.SETTINGS.get('proxy')

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
        project=None,
        folders=None,
        lines_in_file=None,
        lineno=None,
        cursorpos=None,
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
        ua = f'anki-wakatime/{__version__}'
        cmd: list[str] = [
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
            cmd.extend(['--lineno', f'{heartbeat['lineno']}'])
        if heartbeat.get('cursorpos') is not None:
            cmd.extend(['--cursorpos', f'{heartbeat['cursorpos']}'])
        if heartbeat.get('lines_in_file') is not None:
            cmd.extend(['--lines-in-file', f'{heartbeat['lines_in_file']}'])
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
                log(LogLevel.DEBUG if retcode == 102 or retcode == 112 else LogLevel.ERROR, f'wakatime-core exited with status: {retcode}')
            if output:
                log(LogLevel.ERROR, f'wakatime-core output: {output}')
        except:
            log(LogLevel.ERROR, sys.exc_info()[1])


def is_symlink(path):
    return os.path.islink(path) or False
