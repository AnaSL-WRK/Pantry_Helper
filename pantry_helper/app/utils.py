from django.contrib.auth.models import Group

#helper functions for user roles and permissions

ROLE_GROUPS = ['HouseholdAdmin', 'InventoryManager', 'Member', 'Viewer']


def get_user_role(user):
    group = user.groups.filter(name__in=ROLE_GROUPS).first()
    if group:
        return group.name
    return None


def user_has_role(user, role_name):
    return user.groups.filter(name=role_name).exists()