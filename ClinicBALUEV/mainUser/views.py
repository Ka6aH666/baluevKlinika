from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import json
from .services import handle_user_registration
from .utils.db_helpers import get_user_appointment_list

# Create your views here.


def registration(request):
    return handle_user_registration(request)


@login_required
def profile(request):
    user = request.user
    user_appointments = get_user_appointment_list(user)

    context = {'appointments': user_appointments}
    return render(request, "mainUser/profile.html", context=context)
