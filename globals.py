from pathlib import Path
from types import HeartBeatType, LastHeartBeatType
from queue import Queue
import os
import platform

is_win = platform.system() == 'Windows'

HOME_FOLDER: Path = Path(os.environ.get('WAKATIME_HOME')).resolve() or Path.home()

RESOURCES_FOLDER            = HOME_FOLDER / '.wakatime'
CONFIG_FILE                 = HOME_FOLDER / '.wakatime.cfg'
INTERNAL_CONFIG_FILE        = HOME_FOLDER / '.wakatime-internal.cfg'
SETTINGS_FILE               = 'WakaTime.sublime-settings'

SETTINGS = {}

LAST_HEARTBEAT: LastHeartBeatType = {
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
HEARTBEATS: Queue[HeartBeatType]        = Queue()

HEARTBEAT_FREQUENCY             = 2
"""minutes between logging heartbeat when editing same file"""

SEND_BUFFER_SECONDS             = 30
"""seconds between sending buffered heartbeats to API"""

GITHUB_RELEASES_STABLE_URL  = 'https://api.github.com/repos/wakatime/wakatime-cli/releases/latest'
GITHUB_DOWNLOAD_PREFIX      = 'https://github.com/wakatime/wakatime-cli/releases/download'
