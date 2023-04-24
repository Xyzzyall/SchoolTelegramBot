from voice_bot.db.models import User

_user_id_to_chat_id: dict[str, str] = {}
_chat_id_to_user: dict[str, User] = {}


def mock_user(chat_id: str, user: User):
    _user_id_to_chat_id[user.id] = chat_id
    _chat_id_to_user[chat_id] = user


def clear_mock():
    _user_id_to_chat_id.clear()
    _chat_id_to_user.clear()


def is_mocked(subj: User | str) -> bool:
    if isinstance(subj, User):
        return subj.id in _user_id_to_chat_id
    return subj in _chat_id_to_user


def mock_chat_id_to_user(chat_id: str) -> User:
    return _chat_id_to_user[chat_id]


def try_mock_user_to_chat_id(user: User) -> str:
    if user.id not in _user_id_to_chat_id:
        return user.telegram_chat_id
    return _user_id_to_chat_id[user.id]


def try_mock_chat_id(chat_id: str) -> str:
    if chat_id not in _chat_id_to_user:
        return chat_id
    return _chat_id_to_user[chat_id].telegram_chat_id


def try_mock_subj_to_chat_id(subj: User | str) -> str:
    if isinstance(subj, User):
        return try_mock_user_to_chat_id(subj)
    return try_mock_chat_id(subj)
