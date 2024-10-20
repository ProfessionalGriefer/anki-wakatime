from typing import TypedDict


class HeartBeatType(TypedDict):
    """
    Entity represents a file, or in this case a card
    project represents here the deck name
    """
    entity: str
    timestamp: float
    is_write: bool
    project: str
    lines_in_file: int

    # folders: str
    # lineno: NotRequired[int]
    # cursorpos: NotRequired[int]


class LastHeartBeatType(TypedDict):
    time: float
    file: str
    is_write: bool


class SettingsType(TypedDict):
    debug: bool
    ignore: list[str]
    include: list[str]
    hide_file_names: bool
    proxy: str
