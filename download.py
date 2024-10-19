"""
Functions for downloading the CLI from the internet
"""

import os
import platform
import shutil
import threading
import traceback
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from . import globals as g
from .cli import isCliLatest, isCliInstalled, getCliLocation, architecture, getLatestCliVersion
# Custom imports
from .helpers import LogLevel, log, request


class UpdateCLI(threading.Thread):
    """
    Non-blocking thread for downloading latest wakatime-cli from GitHub.
    """

    def run(self):
        if isCliLatest():
            return

        log(LogLevel.INFO, 'Downloading wakatime-cli...')

        # Update for pathlib
        if (g.RESOURCES_FOLDER / 'wakatime-cli').is_dir():
            shutil.rmtree(g.RESOURCES_FOLDER / 'wakatime-cli')

        if not g.RESOURCES_FOLDER.exists():
            g.RESOURCES_FOLDER.mkdir(parents=True)

        try:
            url = cliDownloadUrl()
            log(LogLevel.DEBUG, f'Downloading wakatime-cli from {url}')
            zip_file = g.RESOURCES_FOLDER / 'wakatime-cli.zip'
            download(url, zip_file)

            if isCliInstalled():
                try:
                    getCliLocation().unlink()
                except:
                    log(LogLevel.DEBUG, traceback.format_exc())

            log(LogLevel.INFO, 'Extracting wakatime-cli...')
            with ZipFile(zip_file) as zf:
                zf.extractall(g.RESOURCES_FOLDER)

            if not g.is_win:
                os.chmod(getCliLocation(), 509)  # 755

            try:
                (g.RESOURCES_FOLDER / 'wakatime-cli.zip').unlink()
            except:
                log(LogLevel.DEBUG, traceback.format_exc())
        except:
            log(LogLevel.DEBUG, traceback.format_exc())

        createSymlink()

        log(LogLevel.INFO, 'Finished extracting wakatime-cli.')


def createSymlink():
    """
    Used inside the UpdateCLI class
    :return:
    """
    link: Path = g.RESOURCES_FOLDER
    if g.is_win:
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
            if not g.is_win:
                os.chmod(link, 509)  # 755
        except:
            log(LogLevel.WARNING, traceback.format_exc())


def cliDownloadUrl() -> str:
    """
    Used inside the UpdateCLI class
    :return:
    """

    osname: str = platform.system().lower()
    arch: str = architecture()

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
    check = f'{osname}-{arch}'
    if check not in validCombinations:
        reportMissingPlatformSupport(osname, arch)

    version = getLatestCliVersion()

    prefix = g.GITHUB_DOWNLOAD_PREFIX
    return f'{prefix}/{version}/wakatime-cli-{osname}-{arch}.zip'


def reportMissingPlatformSupport(osname: str, arch: str):
    """
    Used inside cliDownloadUrl()
    :param osname:
    :param arch:
    :return:
    """
    url = f'https://api.wakatime.com/api/v1/cli-missing?osname={osname}&architecture={arch}&plugin=anki'
    request(url)


def download(url, filePath: Path):
    req = Request(url)
    # req.add_header('User-Agent', 'github.com/wakatime/anki-wakatime')

    proxy = g.SETTINGS.get('proxy')
    if proxy:
        req.set_proxy(proxy, 'https')

    with filePath.open(mode='wb') as f:
        try:
            resp = urlopen(req)
            f.write(resp.read())
        except HTTPError as err:
            if err.code == 304:
                return None, None, 304

            log(LogLevel.DEBUG, err.read().decode())
            raise
        except IOError:

            raise
