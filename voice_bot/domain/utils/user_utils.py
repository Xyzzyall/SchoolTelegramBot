from typing import Collection

from voice_bot.db.models import User


def user_has_role(user: User, role: str) -> bool:
    for user_role in user.roles:
        if user_role.role_name == role:
            return True
    return False


def user_has_roles(user: User, roles: Collection[str]) -> bool:
    matches = 0
    for role in user.roles:
        if role.role_name in roles:
            matches += 1

    if matches != len(roles):
        return False

    return True
