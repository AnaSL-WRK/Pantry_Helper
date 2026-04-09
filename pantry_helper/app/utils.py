from django.contrib.auth.models import Group


#aux functions

ROLE_GROUPS = ['HouseholdAdmin', 'InventoryManager', 'Member', 'Viewer']

def get_user_role(user):
    if not user.is_authenticated:
        return None

    group = user.groups.filter(name__in=ROLE_GROUPS).first()
    return group.name if group else None


def get_membership(user):
    return getattr(user, 'household_member', None)


def assign_user_role(user, role_name):
    if role_name not in ROLE_GROUPS:
        raise ValueError(f'Invalid role: {role_name}')

    role_groups = Group.objects.filter(name__in=ROLE_GROUPS)
    user.groups.remove(*role_groups)

    group, _ = Group.objects.get_or_create(name=role_name)
    user.groups.add(group)
    user.save()