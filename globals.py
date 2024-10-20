import os
import platform
from pathlib import Path
from queue import Queue
from typing import Optional

from .customTypes import HeartBeatType, LastHeartBeatType, SettingsType

is_win = platform.system() == 'Windows'

home_variable = os.environ.get('WAKATIME_HOME')
HOME_FOLDER: Path = Path(home_variable).resolve() if home_variable else Path.home()

RESOURCES_FOLDER = HOME_FOLDER / '.wakatime'
CONFIG_FILE = HOME_FOLDER / '.wakatime.cfg'
INTERNAL_CONFIG_FILE = HOME_FOLDER / '.wakatime-internal.cfg'
SETTINGS_FILE = 'WakaTime.sublime-settings'

SETTINGS: SettingsType = {
    "debug": True,
    "ignore": [],
    "include": [],
    "hide_file_names": False,
    "proxy": ""
}

LAST_HEARTBEAT: LastHeartBeatType = {
    'time': 0,
    'file': "",
    'is_write': False,
}

LAST_HEARTBEAT_SENT_AT = 0
LAST_FETCH_TODAY_CODING_TIME = 0
FETCH_TODAY_DEBOUNCE_COUNTER = 0
FETCH_TODAY_DEBOUNCE_SECONDS = 60
LATEST_CLI_VERSION: Optional[str] = None
WAKATIME_CLI_LOCATION: Path = Path()
HEARTBEATS: Queue[HeartBeatType] = Queue()

HEARTBEAT_FREQUENCY = 2
"""minutes between logging heartbeat when editing same file"""

SEND_BUFFER_SECONDS = 30
"""seconds between sending buffered heartbeats to API"""

GITHUB_RELEASES_STABLE_URL = 'https://api.github.com/repos/wakatime/wakatime-cli/releases/latest'
GITHUB_DOWNLOAD_PREFIX = 'https://github.com/wakatime/wakatime-cli/releases/download'
