"""
Managing the wakatime-cli
"""
from pathlib import Path
import platform
import sys
import re
from subprocess import PIPE
import traceback
import json
from configparser import ConfigParser
import globals as g

# Custom imports
from helpers import LogLevel, log, Popen, parseConfigFile
from download import request




def getCliLocation() -> Path:
    """
    Gets the wakatime-cli.exe location and also sets it if it is None
    Used by isCliInstalled(), isCliLatest()
    :return: e.g. HOME_FOLDER / '.wakatime' / 'wakatime-cli-windows-amd64.exe'
    """

    if not g.WAKATIME_CLI_LOCATION:
        binary = 'wakatime-cli-{osname}-{arch}{ext}'.format(
            osname=platform.system().lower(),
            arch=architecture(),
            ext='.exe' if g.is_win else '',
        )
        g.WAKATIME_CLI_LOCATION = g.RESOURCES_FOLDER / binary

    return g.WAKATIME_CLI_LOCATION

def architecture():
    """
    Used within getCliLocation() to get the correct name
    :return:
    """
    arch = platform.machine() or platform.processor()
    if arch == 'armv7l':
        return 'arm'
    if arch == 'aarch64':
        return 'arm64'
    if 'arm' in arch:
        return 'arm64' if sys.maxsize > 2**32 else 'arm'
    return 'amd64' if sys.maxsize > 2**32 else '386'

def isCliInstalled():
    return getCliLocation().exists()

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


def extractVersion(text: str):
    """
    Used inside isCliLatest()
    :param text:
    :return:
    """
    pattern = re.compile(r"([0-9]+\.[0-9]+\.[0-9]+)")
    match = pattern.search(text)
    if match:
        return 'v{ver}'.format(ver=match.group(1))
    return None


def getLatestCliVersion():
    """
    Used inside isCliLatest()
    :return:
    """

    if g.LATEST_CLI_VERSION:
        return g.LATEST_CLI_VERSION

    configs, last_modified, last_version = None, None, None
    try:
        configs: ConfigParser | None = parseConfigFile(g.INTERNAL_CONFIG_FILE)
        if configs:
            last_modified, last_version = lastModifiedAndVersion(configs)
    except:
        log(LogLevel.DEBUG, traceback.format_exc())

    try:
        headers, contents, code = request(g.GITHUB_RELEASES_STABLE_URL, last_modified=last_modified)

        log(LogLevel.DEBUG, f'GitHub API Response {code}')

        if code == 304:
            g.LATEST_CLI_VERSION = last_version
            return last_version

        data = json.loads(contents.decode('utf-8'))

        ver = data['tag_name']
        log(LogLevel.DEBUG, f'Latest wakatime-cli version from GitHub: {ver}')

        if configs:
            last_modified = headers.get('Last-Modified')
            if not configs.has_section('internal'):
                configs.add_section('internal')
            configs.set('internal', 'cli_version', ver)
            configs.set('internal', 'cli_version_last_modified', last_modified)
            with g.INTERNAL_CONFIG_FILE.open(mode='w', encoding='utf-8') as f:
                configs.write(f)

        g.LATEST_CLI_VERSION = ver
        return ver
    except:
        log(LogLevel.DEBUG, traceback.format_exc())
        return None


def lastModifiedAndVersion(configs) -> (str | None, str | None):
    """
    Used inside get LatestCliVersion()
    :param configs:
    :return: last_modified, last_version
    """
    last_modified, last_version = None, None
    if configs.has_option('internal', 'cli_version'):
        last_version = configs.get('internal', 'cli_version')
    if last_version and configs.has_option('internal', 'cli_version_last_modified'):
        last_modified = configs.get('internal', 'cli_version_last_modified')
    if last_modified and last_version and extractVersion(last_version):
        return last_modified, last_version
    return None, None


