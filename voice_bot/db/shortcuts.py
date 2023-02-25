from voice_bot.db.enums import DumpStates

_ACTIVE_DUMP_STATES = [DumpStates.ACTIVE, DumpStates.TO_SYNC]


def is_active(entity):
    return entity.dump_state.in_(_ACTIVE_DUMP_STATES)
