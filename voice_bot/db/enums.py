from enum import Enum


class YesNo(Enum):
    YES = 1,
    NO = 0


class DumpStates(Enum):
    TABLE_DELETED = -2
    BOT_DELETED = -1
    TO_SYNC = 0
    ACTIVE = 1


class ScheduleRecordType(Enum):
    ONLINE = 1
    OFFLINE = 2
    RENT = 3
