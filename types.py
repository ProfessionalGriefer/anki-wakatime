from typing import TypedDict, NotRequired
class HeartBeatType(TypedDict):
    entity: str
    timestamp: float
    is_write: bool
    project: str
    folders: str
    lines_in_file: int

    lineno: NotRequired[int]
    cursorpos: NotRequired[int]


class LastHeartBeatType(TypedDict):
    time: float
    file: str | None
    is_write: bool
