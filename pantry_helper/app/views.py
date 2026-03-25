from django.shortcuts import redirect, render
from pantry_helper.app.utils import user_has_role, get_user_role

# Create your views here.


def home(request):
    return render(request, 'app/home.html')


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    membership = None
    role = get_user_role(request.user)

    if hasattr(request.user, 'household_member'):
        membership = request.user.household_member

    tparams = {
        'membership': membership,
        'role': role,
    }

    return render(request, 'app/dashboard.html', tparams)


def manage_members(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    if not user_has_role(request.user, 'HouseholdAdmin'):
        return redirect('/dashboard/')

    return render(request, 'app/manage_members.html')