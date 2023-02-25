class UserRoles:
    student = "student"

    sysadmin = "sysadmin"
    schedule = "schedule"


class BotRoles:
    user_roles = {
        UserRoles.student: "Ученик"
    }
    user_roles_names = {}

    admin_roles = {
        UserRoles.sysadmin: "Управление ботом",
        UserRoles.schedule: "Расписание"
    }
    admin_roles_names = {}


for k, v in BotRoles.user_roles.items():
    BotRoles.user_roles_names[v] = k

for k, v in BotRoles.admin_roles.items():
    BotRoles.admin_roles_names[v] = k