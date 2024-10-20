# -*- coding: utf-8 -*-
""" ==========================================================
File:        WakaTime.py
Description: Automatic time tracking for Anki
Maintainer:  Vincent Nahn
License:     BSD 3, see LICENSE for more details.
Website:     https://github.com/ProfessionalGriefer/anki-wakatime
Debug:       https://wakatime.com/plugins/status
==========================================================="""

__version__ = '0.1'

import json
import threading
import time
from queue import Empty as QueueEmpty
from subprocess import STDOUT, PIPE


# Imports for Anki
from anki.cards import Card
from anki.collection import Collection
from aqt.qt import *
from aqt.utils import showInfo
from aqt import mw

if mw is not None:
    ankiConfig = mw.addonManager.getConfig(__name__) or {}
else:
    ankiConfig = {}

from . import globals as g
from .cli import isCliInstalled, getCliLocation
from .helpers import LogLevel, log, Popen, obfuscate_apikey, set_timeout, enough_time_passed
from .customTypes import HeartBeatType


class ApiDialogWidget(QInputDialog):
    """
    Used within the ApiKey class to get the API key from the user if none has been found in the config
    Must be a class because it is displaying a new QtWidget
    :return: API key
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def prompt(self) -> str:
        promptText = "Enter the WakaTime API Key"
        wakaKeyTemplate = "waka_XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
        key, ok = QInputDialog.getText(self, promptText, wakaKeyTemplate)

        if ok and key and mw:
            # Save the text to addon's config
            ankiConfig["wakaTime-api-key"] = key
            mw.addonManager.writeConfig(__name__, ankiConfig)

            # Optionally show a message confirming it was saved
            showInfo("Your new API key has been saved")

            return key

        else:
            print("An error occurred while saving the API key")

        return ""


class ApiKey(object):
    _key: str = ""

    def read(self) -> str:
        """
        :return: API key; empty if none have been found
        """
        if self._key != "":
            return self._key

        # Read from the Anki Addon Config
        key: str = ankiConfig['wakaTime-api-key']
        if key and key != "":
            self._key = key
            return self._key

        # Else prompt for the API Key
        dialog = ApiDialogWidget()
        key = dialog.prompt()

        if key and key != "":
            self._key = key
            return key

        print("Empty key :(")
        return ""


APIKEY = ApiKey()


def handle_activity(card: Card, is_write=False):
    # Get the first value of dict, hopefully that is the main question of the card
    entity: str = next(iter(card.note().values()))
    timestamp: float = time.time()
    last_file: str = g.LAST_HEARTBEAT['file']
    print(entity, timestamp, last_file)
    if entity != last_file or enough_time_passed(timestamp, is_write):
        col: Collection = card.col
        deck_id = card.did
        project = col.decks.name(deck_id)
        append_heartbeat(entity, timestamp, is_write, project)


def append_heartbeat(entity: str, timestamp: float, is_write: bool, project: str):
    # add this heartbeat to queue
    heartbeat: HeartBeatType = {
        'entity': entity,
        'timestamp': timestamp,
        'is_write': is_write,
        'project': project,
        'lines_in_file': len(entity.split('\n'))
    }
    g.HEARTBEATS.put_nowait(heartbeat)

    # make this heartbeat the LAST_HEARTBEAT
    g.LAST_HEARTBEAT = {
        'time': timestamp,
        'file': entity,
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


def build_heartbeat(
        entity,
        timestamp,
        is_write,
        project,
        lines_in_file=0,
) -> HeartBeatType:
    """Returns a dict for passing to wakatime-cli as arguments."""
    heartbeat: HeartBeatType = {
        'entity': entity,
        'timestamp': timestamp,
        'is_write': is_write,
        'project': project,
        'lines_in_file': lines_in_file,
    }

    return heartbeat


class SendHeartbeatsThread(threading.Thread):
    """Non-blocking thread for sending heartbeats to api.
    """

    def __init__(self, heartbeat):
        threading.Thread.__init__(self)

        self.debug = g.SETTINGS.get('debug')
        self.api_key = APIKEY.read() or ''
        self.ignore = g.SETTINGS.get('ignore', [])
        self.include = g.SETTINGS.get('include', [])
        self.hideFileNames = g.SETTINGS.get('hide_file_names')
        self.proxy = g.SETTINGS.get('proxy')

        self.heartbeat = heartbeat
        self.has_extra_heartbeats = False
        self.extra_heartbeats = None

    def add_extra_heartbeats(self, extra_heartbeats) -> None:
        self.has_extra_heartbeats = True
        self.extra_heartbeats = extra_heartbeats

    def run(self):
        """Running in background thread."""

        self.send_heartbeats()

    def send_heartbeats(self):
        heartbeat = build_heartbeat(**self.heartbeat)
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
        if heartbeat.get('lines_in_file') != 0:
            cmd.extend(['--lines-in-file', f'{heartbeat["lines_in_file"]}'])
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
            extra_heartbeats = json.dumps([build_heartbeat(**x) for x in self.extra_heartbeats])
            inp = "{0}\n".format(extra_heartbeats).encode('utf-8')
        else:
            self.extra_heartbeats = None
            stdin = None
            inp = None

        log(LogLevel.DEBUG, ' '.join(obfuscate_apikey(cmd)))
        try:
            process = Popen(cmd, stdin=stdin, stdout=PIPE, stderr=STDOUT)
            output, _err = process.communicate(input=inp)
            retcode = process.poll()
            if retcode:
                log(LogLevel.DEBUG if retcode == 102 or retcode == 112 else LogLevel.ERROR,
                    f'wakatime-core exited with status: {retcode}')
            if output:
                log(LogLevel.ERROR, f'wakatime-core output: {output}')
        except:
            log(LogLevel.ERROR, sys.exc_info()[1])
