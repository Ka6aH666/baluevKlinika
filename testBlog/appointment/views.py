from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .decorators import require_ajax
from .forms import AppointmentRequestForm, SlotForm
from .models import Appointment, CalendarSettings, DayOff, Service, StaffMember
from .services import get_appointments_and_slots, get_available_slots_for_staff
from .utils.db_helpers import (check_day_off_for_staff,
                               create_and_save_appointment,
                               get_non_working_days_for_staff,
                               get_weekday_num_from_date, is_working_day)
from .utils.error_codes import ErrorCode
from .utils.json_context import get_generic_context_with_extra, json_response


# Create your views here.
def get_available_slots_ajax(request):
    """This view function handles AJAX requests to get available slots for a selected date.

    :param request: The request instance.
    :return: A JSON response containing available slots, selected date, an error flag, and an optional error message.
    """
    slot_form = SlotForm(request.GET)
    error_code = 0
    if not slot_form.is_valid():
        custom_data = {"error": True, "available_slots": [], "date_chosen": ""}
        if "selected_date" in slot_form.errors:
            error_code = ErrorCode.PAST_DATE
        elif "staff_member" in slot_form.errors:
            error_code = ErrorCode.STAFF_ID_REQUIRED
        message = list(slot_form.errors.as_data().items())[0][1][0].messages[
            0
        ]  # dirty way to keep existing behavior
        return json_response(
            message=message,
            custom_data=custom_data,
            success=False,
            error_code=error_code,
        )
    selected_date = slot_form.cleaned_data["selected_date"]
    sm = slot_form.cleaned_data["staff_member"]
    service = slot_form.cleaned_data["service"]
    date_chosen = selected_date.strftime("%a, %B %d, %Y")
    date_look = selected_date
    custom_data = {"date_chosen": date_chosen, "date_look": date_look}

    days_off_exist = check_day_off_for_staff(staff_member=sm, date=selected_date)

    if days_off_exist:
        message = _("Day off, please select another day.")
        custom_data["available_slots"] = []
        return json_response(
            message=message,
            custom_data=custom_data,
            success=False,
            error_code=ErrorCode.INVALID_DATE,
        )
    # if selected_date is not a working day for the staff, return an empty list of slots and 'message' is Day Off
    weekday_num = get_weekday_num_from_date(selected_date)
    is_working_day_ = is_working_day(staff_member=sm, day=weekday_num)
    custom_data["staff_member"] = sm.get_staff_member_name()
    if not is_working_day_:
        message = (
            "{staff_member} Не работает в этот день. Выберите другой".format(
                staff_member=sm.get_staff_member_name()
            )
        )
        custom_data["available_slots"] = []
        return json_response(
            message=message,
            custom_data=custom_data,
            success=False,
            error_code=ErrorCode.INVALID_DATE,
        )
    available_slots = get_available_slots_for_staff(selected_date, sm, service)

    # Check if the selected_date is today and filter out past slots
    if selected_date == date.today():
        current_time = timezone.now()
        moscow_now = current_time.astimezone(timezone.get_current_timezone())
        available_slots = [
            slot for slot in available_slots if slot.time() > moscow_now.time()
        ]

    custom_data["available_slots"] = [
        slot.strftime("%H:%M") for slot in available_slots
    ]
    if len(available_slots) == 0:
        custom_data["error"] = True
        message = "Нет доступных слотов на этот день"
        return json_response(
            message=message,
            custom_data=custom_data,
            success=False,
            error_code=ErrorCode.INVALID_DATE,
        )
    custom_data["error"] = False
    return json_response(
        message="Successfully retrieved available slots",
        custom_data=custom_data,
        success=True,
    )


def create_appointment(request, appointment_request_id):
    """This function creates a new appointment and redirects to the payment page or the thank-you page.

    :param request: The request instance.
    :param appointment_request_id: The AppointmentRequest instance.
    :return: The redirect response.
    """
    appointment = create_and_save_appointment(appointment_request_id, request)
    return redirect_to_payment_or_thank_you_page(appointment)


def default_thank_you(request, appointment_id):
    """This view function handles the default thank you page.

    :param request: The request instance.
    :param appointment_id: The ID of the appointment.
    :return: The rendered HTML page.
    """
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    extra_context = {
        "appointment": appointment,
    }
    context = get_generic_context_with_extra(request, extra_context, admin=False)
    return render(request, "appointment/default_thank_you.html", context=context)


def redirect_to_payment_or_thank_you_page(appointment):
    """This function redirects to the payment page or the thank-you page based on the configuration.

    :param appointment: The Appointment instance.
    :return: The redirect response.
    """
    thank_you_url_key = "default_thank_you"
    thank_you_url = reverse(
        thank_you_url_key, kwargs={"appointment_id": appointment.id}
    )
    return HttpResponseRedirect(thank_you_url)


@require_ajax
def get_next_available_date_ajax(request, service_id):
    """This view function handles AJAX requests to get the next available date for a service.

    :param request: The request instance.
    :param service_id: The ID of the service.
    :return: A JSON response containing the next available date.
    """
    staff_id = request.GET.get("staff_member")

    # If staff_id is not provided, you should handle it accordingly.
    if staff_id and staff_id != "none":
        staff_member = get_object_or_404(StaffMember, pk=staff_id)
        service = get_object_or_404(Service, pk=service_id)

        # Fetch the days off for the staff
        days_off = DayOff.objects.filter(staff_member=staff_member).filter(
            Q(start_date__lte=date.today(), end_date__gte=date.today())
            | Q(start_date__gte=date.today())
        )

        current_date = date.today()
        next_available_date = None
        day_offset = 0

        while next_available_date is None:
            potential_date = current_date + timedelta(days=day_offset)

            # Check if the potential date is a day off for the staff
            is_day_off = any(
                [
                    day_off.start_date <= potential_date <= day_off.end_date
                    for day_off in days_off
                ]
            )
            # Check if the potential date is a working day for the staff
            weekday_num = get_weekday_num_from_date(potential_date)
            is_working_day_ = is_working_day(staff_member=staff_member, day=weekday_num)

            if not is_day_off and is_working_day_:
                x, available_slots = get_appointments_and_slots(potential_date, service)
                if available_slots:
                    next_available_date = potential_date

            day_offset += 1
        message = "Successfully retrieved next available date"
        data = {"next_available_date": next_available_date.isoformat()}
        return json_response(message=message, custom_data=data, success=True)
    else:
        data = {"error": True}
        message = _("No staff member selected")
        return json_response(
            message=message,
            custom_data=data,
            success=False,
            error_code=ErrorCode.STAFF_ID_REQUIRED,
        )


def appointment_request(request, service_id=None, staff_member_id=None):
    """This view function handles requests to book an appointment for a service.

    :param request: The request instance.
    :param service_id: The ID of the service.
    :param staff_member_id: The ID of the staff member.
    :return: The rendered HTML page.
    """

    service = None
    staff_member = None
    all_staff_members = None
    available_slots = []
    label = 'BALUEV'
    if not request.user.is_authenticated:
        messages.error(request, _("To recording you must be registered"))
        return redirect("services")
    if service_id:
        service = get_object_or_404(Service, pk=service_id)
        all_staff_members = StaffMember.objects.filter(services_offered=service)

        # If only one staff member for a service, choose them by default and fetch their slots.
        if all_staff_members.count() == 1:
            staff_member = all_staff_members.first()
            x, available_slots = get_appointments_and_slots(date.today(), service)

    # If a specific staff member is selected, fetch their slots.
    if staff_member_id:
        staff_member = get_object_or_404(StaffMember, pk=staff_member_id)
        y, available_slots = get_appointments_and_slots(date.today(), service)

    date_chosen = date.today().strftime("%a, %B %d, %Y")
    date_look = date.today()
    extra_context = {
        "service": service,
        "staff_member": staff_member,
        "all_staff_members": all_staff_members,
        "available_slots": available_slots,
        "date_chosen": date_chosen,
        "date_look": date_look,
        "label": label,
    }
    context = get_generic_context_with_extra(request, extra_context, admin=False)
    return render(request, "appointment/appointments.html", context=context)


def appointment_request_submit(request):
    """This view function handles the submission of the appointment request form.

    :param request: The request instance.
    :return: The rendered HTML page.
    """
    if request.method == "POST":
        form = AppointmentRequestForm(request.POST)
        if form.is_valid():
            # Use form.cleaned_data to get the cleaned and validated data
            staff_member = form.cleaned_data["staff_member"]
            staff_exists = StaffMember.objects.filter(id=staff_member.id).exists()
            if not staff_exists:
                messages.error(request, "Selected staff member does not exist.")
            else:
                ar = form.save()
                return render(request, "appointment/confirm_appt.html", {'appointment_request': ar})
        else:
            # Handle the case if the form is not valid
            messages.error(
                request,
                _("There was an error in your submission. Please check the form and try again."),
            )
    else:
        form = AppointmentRequestForm()

    context = get_generic_context_with_extra(request, {"form": form}, admin=False)
    return render(request, "appointment/appointments.html", context=context)


def confirm_appt(request, appointment_request_id):
    return create_appointment(request, appointment_request_id)


def get_non_working_days_ajax(request):
    staff_id = request.GET.get("staff_member")
    error = False
    message = "Successfully retrieved non-working days"

    if not staff_id or staff_id == "none":
        message = "No staff member selected"
        error_code = ErrorCode.STAFF_ID_REQUIRED
        error = True
    else:
        non_working_days = get_non_working_days_for_staff(staff_id)
        staff_member = StaffMember.objects.get(id=staff_id)
        day_off = set(
            DayOff.objects.filter(staff_member=staff_member).values_list(
                "start_date", "end_date",
            )
        )
        custom_data = {"non_working_days": non_working_days, "day_off": list(day_off)}
        return json_response(
            message=message, custom_data=custom_data, success=not error
        )

    custom_data = {"error": error}
    return json_response(
        message=message,
        custom_data=custom_data,
        success=not error,
        error_code=error_code,
    )


def show_services(request):
    services = Service.objects.all()
    context = {"services": services}
    return render(request, "appointment/show_services.html", context)


def get_calender_settings_for_staff_ajax(request):
    staff_id = request.GET.get("staff_member")
    calender_settings, created = CalendarSettings.objects.get_or_create(staff_member=staff_id)
    error = False
    message = "Successfully retrieved staff settings"
    if not staff_id or staff_id == "none":
        message = "No staff member selected"
        error_code = ErrorCode.STAFF_ID_REQUIRED
        error = True
    else:
        calender_start_date = date.today()
        calender_end_date = calender_settings.get_end_date()
        custom_data = {"calender_start_date": calender_start_date, "calender_end_date": calender_end_date}

        return json_response(
            message=message, custom_data=custom_data, success=not error
        )

    custom_data = {"error": error}
    return json_response(
        message=message,
        custom_data=custom_data,
        success=not error,
        error_code=error_code,
    )
