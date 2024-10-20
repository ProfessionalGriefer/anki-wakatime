"""
Options for the wakatime-cli command
Serves only as a reference, not used anywhere else
"""
from typing import Any

SETTINGS: dict[str, Any]  = {
    # Optional alternate language name. Auto-detected language takes priority.
    # "alternate-language": "Other",

    # Optional alternate project name. Auto-detected project takes priority.
    # "alternate-project": "Anki",

    # API base url used when sending heartbeats and fetching code stats. Defaults to https://api.wakatime.com/api/v1/.
    "api-url": "https://api.wakatime.com/api/v1/",

    # Category of this heartbeat activity. Can be "coding", "building", "indexing", "debugging", "communicating", "supporting", "advising", "running tests", "writing tests", "manual testing", "code reviewing", "browsing", or "designing". Defaults to "coding".
    "category": "Flashcards",

    # Optional config file. Defaults to '~/.wakatime.cfg'.
    "config": "~/.wakatime.cfg",

    # Prints value for the given config key, then exits.
    # "config-read" string

    # Optional config section when reading or writing a config key. Defaults to [settings]. (default "settings")
    "config-section": "settings",

    # Writes value to a config key, then exits. Expects two arguments, key and value. (default [])
    # "config-write" stringToString

    # Optional cursor position in the current file.
    "cursorpos": None,

    # Disables offline time logging instead of queuing logged time.
    # "disable-offline"

    # Absolute path to file for the heartbeat. Can also be a url, domain or app when entity-type is not file.
    "entity": "Anki",

    # Entity type for this heartbeat. Can be "file", "domain" or "app". Defaults to "file".
    "entity-type": "app",

    # Filename patterns to exclude from logging. POSIX regex syntax. Can be used more than once.
    # "exclude" strings

    # When set, any activity where the project cannot be detected will be ignored.
    # "exclude-unknown-project"

    # Reads extra heartbeats from STDIN as a JSON array until EOF.
    # "extra-heartbeats"

    # help for wakatime-cli
    # "help"

    # Obfuscate branch names. Will not send revision control branch names to api.
    # "hide-branch-names" string

    # Obfuscate filenames. Will not send file names to api.
    "hide-file-names": None,

    # Obfuscate project names. When a project folder is detected instead of using the folder name as the project, a .wakatime-project file is created with a random project name.
    # "hide-project-names" string

    # Optional name of local machine. Defaults to local machine name read from system.
    # "hostname" string

    # Filename patterns to log. When used in combination with exclude, files matching include will still be logged. POSIX regex syntax. Can be used more than once.
    "include": [],

    # Disables tracking folders unless they contain a .wakatime-project file. Defaults to false.
    # "include-only-with-project-file"

    # Optional internal config file. Defaults to '~/.wakatime-internal.cfg'.
    "internal-config": "~/.wakatime-internal.cfg",

    # Your wakatime api key; uses api_key from ~/.wakatime.cfg by default.
    "key": "",

    # Optional language name. If valid, takes priority over auto-detected language.
    "language": "Other",

    # Optional line number. This is the current line being edited.
    # "lineno" int

    # Optional lines in the file. Normally, this is detected automatically but can be provided manually for performance, accuracy, or when using local-file.
    # "lines-in-file" int

    # Absolute path to local file for the heartbeat. When entity is a remote file, this local file will be used for stats and just the value of entity is sent with the heartbeat.
    # "local-file" string

    # Optional log file. Defaults to '~/.wakatime/wakatime.log'.
    "log-file": "~/.wakatime/wakatime.log",

    # If enabled, logs will go to stdout. Will overwrite logfile configs.
    # "log-to-stdout"

    # Disables SSL certificate verification for HTTPS requests. By default, SSL certificates are verified.
    # "no-ssl-verify"

    # Prints the number of heartbeats in the offline db, then exits.
    # "offline-count"

    # Optional text editor plugin name and version for User-Agent header.
    "plugin": None,

    # Override auto-detected project. Use alternate-project to supply a fallback project if one can't be auto-detected.
    "project": "Anki",

    # Optional proxy configuration. Supports HTTPS SOCKS and NTLM proxies. For example: 'https://user:pass@host:port' or 'socks5://user:pass@host:port' or 'domain\user:pass'
    "proxy": None,

    # Override the bundled CA certs file. By default, uses system ca certs.
    # "ssl-certs-file" string

    # Amount of offline activity to sync from your local ~/.wakatime/offline_heartbeats.bdb bolt file to your WakaTime Dashboard before exiting. Can be "none" or a positive integer. Defaults to 1000, meaning after sending a heartbeat while online, all queued offline heartbeats are sent to WakaTime API, up to a limit of 1000. Can be used without entity to only sync offline activity without generating new heartbeats. (default "1000")
    "sync-offline-activity": 1000,

    # Optional floating-point unix epoch timestamp. Uses current time by default.
    "time": None,

    # Number of seconds to wait when sending heartbeats to api. Defaults to 120 seconds. (default 120)
    "timeout": 120,

    # Prints dashboard time for Today, then exits.
    # "today"

    # Prints time for the given goal id Today, then exits Visit wakatime.com/api/v1/users/current/goals to find your goal id.
    # "today-goal" string

    # When optionally included with today, causes output to show total code time today without categories.
    # "today-hide-categories"

    # Turns on debug messages in log file.
    # "verbose"

    # Prints the wakatime-cli version number, then exits.
    # "version"

    # When set, tells api this heartbeat was triggered from writing to a file.
    "write": False
}
