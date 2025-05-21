import datetime
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from .forms import (PersonalInformationForm, ServiceForm, StaffDaysOffForm,
                    StaffWorkingHoursForm)
from .models import (Appointment, AppointmentRequest, ArchivedAppointment,
                     ArchivedAppointmentRequest, CalendarSettings, Service,
                     StaffMember, WorkingHours)
from .utils.date_time import convert_str_to_time, get_ar_end_time
from .utils.db_helpers import (calculate_slots, calculate_staff_slots,
                               day_off_exists_for_date_range,
                               exclude_booked_slots, get_all_appointments,
                               get_appointments_for_date_and_time,
                               get_staff_member_appointment_list,
                               get_staff_member_from_user_id_or_logged_in,
                               get_times_from_config,
                               get_weekday_num_from_date,
                               get_working_hours_for_staff_and_day, parse_name,
                               working_hours_exist)
from .utils.error_codes import ErrorCode
from .utils.json_context import (convert_appointment_to_json,
                                 get_generic_context, json_response)


def get_available_slots_for_staff(date, staff_member, service: Service):
    """Calculate the available time slots for a given date and a staff member.

    :param date: The date for which to calculate the available slots
    :param staff_member: The staff member for which to calculate the available slots
    :param service: service_id
    :return: A list of available time slots as strings in the format '%I:%M %p' like ['10:00 AM', '10:30 AM']
    """

    # Check if the staff member works on the provided date
    day_of_week = get_weekday_num_from_date()
    # Python's weekday starts from Monday (0) to Sunday (6)
    working_hours_dict = get_working_hours_for_staff_and_day(staff_member, day_of_week)
    if not working_hours_dict:
        return []

    slot_duration = datetime.timedelta(minutes=staff_member.get_slot_duration())
    slots = calculate_staff_slots(date, staff_member)
    appointments = get_appointments_for_date_and_time(
        date,
        working_hours_dict["start_time"],
        working_hours_dict["end_time"],
        staff_member,
    )
    return exclude_booked_slots(appointments, slots, slot_duration, service.duration)


def get_available_slots(date, appointments, service_duration):
    """Calculate the available time slots for a given date and a list of appointments.

    :param date: The date for which to calculate the available slot
    :param appointments: A list of Appointment objects
    :return: A list of available time slots as strings in the format '%I:%M %p' like ['10:00 AM', '10:30 AM']
    """

    start_time, end_time, slot_duration, buff_time = get_times_from_config(date)
    now = timezone.now()
    moscow_now = now.astimezone(timezone.get_current_timezone())
    buffer_time = moscow_now + buff_time if date == now.date() else moscow_now
    slots = calculate_slots(start_time, end_time, buffer_time, slot_duration)
    slots = exclude_booked_slots(appointments, slots, slot_duration, service_duration)
    return [slot.strftime("%I:%M %p") for slot in slots]


def handle_service_management_request(post_data, files_data=None, service_id=None):
    try:
        if service_id:
            service = Service.objects.get(pk=service_id)
            form = ServiceForm(post_data, files_data, instance=service)
        else:
            form = ServiceForm(post_data, files_data)

        if form.is_valid():
            form.save()
            return form.instance, True, "Service saved successfully."
    except Exception as e:
        return None, False, str(e)


def get_appointments_and_slots(date_, service=None):
    """
    Get appointments and available slots for a given date and service.

    If a service is provided, the function retrieves appointments for that service on the given date.
    Otherwise, it retrieves all appointments for the given date.

    :param date_: datetime.date, the date for which to retrieve appointments and available slots
    :param service: Service, the service for which to retrieve appointments
    :return: tuple, a tuple containing two elements:
        - A queryset of appointments for the given date and service (if provided).
        - A list of available time slots on the given date, excluding booked appointments.
    """
    if service:
        appointments = Appointment.objects.filter(
            appointment_request__service=service, appointment_request__date=date_
        )
    else:
        appointments = Appointment.objects.filter(appointment_request__date=date_)
    service_duration = service.duration
    available_slots = get_available_slots(date_, appointments, service_duration)
    return appointments, available_slots


def prepare_user_profile_data(user, staff_user_id):
    """Prepare the data for the user profile page."""
    staff_member = get_staff_member_from_user_id_or_logged_in(user, staff_user_id)
    print(staff_member, "if user.staffmember is not None")
    bt_help = StaffMember._meta.get_field("appointment_buffer_time")
    bt_help_text = bt_help.help_text


    settings, created = CalendarSettings.objects.get_or_create(staff_member=staff_member)

    sd_help = StaffMember._meta.get_field("slot_duration")
    sd_help_text = sd_help.help_text
    service_msg = "Здесь вы можете добавлять/удалять предлагаемые вами услуги, изменяя этот раздел."
    data = {
        "error": False,
        "template": "administration/user_profile.html",
        "extra_context": {
            "superuser": user if user.is_superuser else None,
            "staff_member": staff_member if staff_member else user,
            "days_off": staff_member.get_days_off().order_by("start_date")
            if staff_member
            else [],
            "working_hours": staff_member.get_working_hours() if staff_member else [],
            "services_offered": staff_member.get_services_offered()
            if staff_member
            else [],
            "staff_member_not_found": not bool(staff_member),
            "buffer_time_help_text": bt_help_text,
            "slot_duration_help_text": sd_help_text,
            "service_msg": service_msg,
            "settings": settings,
            "start_date": date.today(),
        },
    }
    return data


def check_exists_calander_settings(request, staff_user_id):
    print("НА входе ,kznm", staff_user_id, request.user.id, request.user)
    staff_membersi = StaffMember.objects.all()
    for i in staff_membersi:
        print(i.user, "id=", i.user.id, "id_staff=", i.id)
    if request.user.is_superuser:
        staff_member = StaffMember.objects.get(user=staff_user_id)
    elif int(staff_user_id) == request.user.id:
        staff_member = StaffMember.objects.get(user=staff_user_id)
    else:
        staff_member = None
        settings = None
        return staff_member, settings
    print("НОРМ", staff_member, request.user.id)
    settings, created = CalendarSettings.objects.get_or_create(staff_member=staff_member)
    return staff_member, settings


def update_personal_info_service(staff_user_id, post_data, current_user):
    try:
        user = (
            get_user_model().objects.get(pk=staff_user_id)
            if staff_user_id
            else current_user
        )
    except get_user_model().DoesNotExist:
        return None, False, "Пользователь не найден."

    form = PersonalInformationForm(post_data, user=user)
    if form.is_valid():
        user.first_name = form.cleaned_data["first_name"]
        user.last_name = form.cleaned_data["last_name"]
        user.email = form.cleaned_data["email"]
        user.save()
        return user, True, None
    else:
        return None, False, "Заполните все поля"


def fetch_user_appointments(user):
    """Fetch the appointments for a given user.

    :param user: The user instance.
    :return: A list of appointments.
    """
    if user.is_superuser:
        return get_all_appointments()
    try:
        staff_member_instance = user.staffmember
        return get_staff_member_appointment_list(staff_member_instance)
    except ObjectDoesNotExist:
        if user.is_staff:
            return []

    raise ValueError("User is not a staff member or a superuser")


def prepare_appointment_display_data(user, appointment_id):
    """Prepare the data for the appointment details page.

    :param user: The user instance.
    :param appointment_id: The appointment id.
    :return: A tuple containing the appointment instance, page title, error message, and status code.
    """
    appointment = Appointment.objects.get(id=appointment_id)

    # If the appointment doesn't exist
    if not appointment:
        return None, None, "Appointment does not exist.", 404

    # Prepare the data for display
    page_title = "Детали услуги" + ": {client_name}".format(client_name=appointment.get_client_name())
    if user.is_superuser:
        page_title += f' (у: {appointment.get_staff_member_name()})'

    return appointment, page_title, None, 200


def create_new_appt_from_calender_modal(data, request):
    service = Service.objects.get(id=data.get("service_id"))
    staff_id = data.get("staff_member")
    if staff_id:
        staff_member = StaffMember.objects.get(id=staff_id)
    else:
        staff_member = StaffMember.objects.get(user=request.user)

    client_id = data.get("user_id")
    date = data.get("date")
    start_time = data.get("start_time")
    date_object = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    time_object = datetime.datetime.strptime(start_time, "%H:%M").time()
    start_datetime = datetime.datetime.combine(date_object, time_object)

    appointment_request = AppointmentRequest(
        date=start_datetime.date(),
        start_time=start_datetime.time(),
        end_time=(start_datetime + service.duration).time(),
        service=service,
        staff_member=staff_member,
    )
    appointment_request.full_clean()  # Validates the model
    appointment_request.save()

    user = get_object_or_404(get_user_model(), pk=client_id)
    appointment = Appointment.objects.create(
        client=user, appointment_request=appointment_request
    )
    appointment.save()
    appointment_list = convert_appointment_to_json(request, [appointment])

    return json_response("Appointment created successfully.", custom_data={'appt': appointment_list})


def update_existing_appointment(data, request):
    try:
        appt = Appointment.objects.get(id=data.get("appointment_id"))
        staff_id = data.get("staff_member")
        appt = save_appointment(
            appt,
            client_name=data.get("client_name"),
            client_email=data.get("client_email"),
            start_time=data.get("start_time"),
            phone_number=data.get("client_phone"),
            service_id=data.get("service_id"),
            not_come=data.get("not_come"),
            social_link_tg=data.get("social_link_tg"),
            social_link_vk=data.get("social_link_vk"),
            staff_member_id=staff_id,
        )
        if not appt:
            return json_response("Service not offered by staff member.", status=400, success=False,
                                 error_code=ErrorCode.SERVICE_NOT_FOUND)
        appointments_json = convert_appointment_to_json(request, [appt])[0]
        return json_response(_("Запись на прием успешно обновлена."), custom_data={'appt': appointments_json})
    except Appointment.DoesNotExist:
        return json_response("Appointment does not exist.", status=404, success=False,
                             error_code=ErrorCode.APPOINTMENT_NOT_FOUND)
    except Service.DoesNotExist:
        return json_response("Service does not exist.", status=404, success=False,
                             error_code=ErrorCode.SERVICE_NOT_FOUND)
    except Exception as e:
        return json_response(str(e.args[0]), status=400, success=False)


def save_appointment(appt, client_name, client_email, start_time, phone_number, service_id, not_come, social_link_tg,
                     social_link_vk,
                     staff_member_id=None):
    """Save an appointment's details.
    :return: The modified appointment.
    """
    service = Service.objects.get(id=service_id)
    if staff_member_id:
        staff_member = StaffMember.objects.get(id=staff_member_id)
        if not staff_member.get_service_is_offered(service_id):
            return None

    # Modify and save client details
    first_name, last_name = parse_name(client_name)
    client = appt.client
    client.first_name = first_name
    client.last_name = last_name
    client.social_link_tg = social_link_tg
    client.social_link_vk = social_link_vk
    client.email = client_email
    client.phone_number = phone_number
    client.save()

    # convert start time to a time object if it is a string
    if isinstance(start_time, str):
        start_time = convert_str_to_time(start_time)
    # calculate end time from start time and service duration
    end_time = get_ar_end_time(start_time, service.duration)

    # Modify and save appointment request details
    appt_request = appt.appointment_request

    appt_request.service = service
    appt_request.start_time = start_time
    appt_request.end_time = end_time
    appt_request.staff_member = staff_member
    appt_request.save()

    # Modify and save appointment details
    appt.not_come = not_come
    appt.save()
    return appt


def save_appt_date_time(appt_start_time, appt_date, appt_id, request):
    """Save the date and time of an appointment request.

    :param appt_start_time: The start time of the appointment request.
    :param appt_date: The date of the appointment request.
    :param appt_id: The ID of the appointment to modify.
    :param request: The request object.
    :return: The modified appointment.
    """
    appt = Appointment.objects.get(id=appt_id)
    service = appt.get_service()

    # Convert start time to a time object if it is a string
    if isinstance(appt_start_time, str):
        time_format = "%H:%M:%S.%fZ"
        appt_start_time_obj = datetime.datetime.strptime(appt_start_time, time_format).time()
    else:
        appt_start_time_obj = appt_start_time

    # Calculate end time from start time and service duration
    end_time_obj = get_ar_end_time(appt_start_time_obj, service.duration)

    # Convert the appt_date from string to a date object if it's a string
    if isinstance(appt_date, str):
        appt_date_obj = datetime.datetime.strptime(appt_date, "%Y-%m-%d").date()
    else:
        appt_date_obj = appt_date

    # Modify and save appointment request details
    appt_request = appt.appointment_request
    appt_request.date = appt_date_obj
    appt_request.start_time = appt_start_time_obj
    appt_request.end_time = end_time_obj
    appt_request.save()
    appt.save()

    return appt


def handle_entity_management_request(
        request,
        staff_member,
        entity_type,
        instance=None,
        staff_user_id=None,
        instance_id=None,
        add=True,
):
    if not staff_member:
        return json_response(
            "Not authorized",
            status=403,
            success=False,
            error_code=ErrorCode.NOT_AUTHORIZED,
        )

    button_text = "Сохранить" if instance else "Добавить"
    if entity_type == "day_off":
        form = StaffDaysOffForm(instance=instance)
        context = get_working_hours_and_days_off_context(
            request, button_text, "day_off_form", form
        )
        template = "administration/manage_day_off.html"
    else:
        form = StaffWorkingHoursForm(instance=instance)
        context = get_working_hours_and_days_off_context(
            request,
            button_text,
            "working_hours_form",
            form,
            staff_user_id,
            instance,
            instance_id,
        )
        template = "administration/manage_working_hours.html"

    if request.method == "POST" and entity_type == "day_off":
        day_off_form = StaffDaysOffForm(request.POST, instance=instance)
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        if day_off_exists_for_date_range(
                staff_member, start_date, end_date, getattr(instance, "id", None)
        ):
            messages.error(request, "Такие выходные уже установлены")
            redirect_url = reverse(
                "add_day_off", kwargs={"staff_user_id": staff_member.user.id}
            )
            return json_response(custom_data={"redirect_url": redirect_url})
        return handle_day_off_form(day_off_form, staff_member)

    elif request.method == "POST" and entity_type == "working_hours":
        day_of_week = request.POST.get("day_of_week")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        return handle_working_hours_form(
            staff_member, day_of_week, start_time, end_time, add, instance_id
        )

    return render(request, template, context, status=200)


def get_working_hours_and_days_off_context(
        request, btn_txt, form_name, form, user_id=None, instance=None, wh_id=None
):
    """Get the context for the working hours and days off forms.

    :param request: The request object.
    :param btn_txt: The text to display on the submit button.
    :param form_name: The name of the form which depends on if it's a working hours or days off form.
    :param form: The form instance itself.
    :param user_id: The staff user id.
    :param instance: The working hour form instance.
    :param wh_id: The working hour id.
    :return: A dictionary containing the context.
    """
    context = get_generic_context(request)
    now = timezone.now()
    moscow_now = now.astimezone(timezone.get_current_timezone())
    context.update(
        {
            "button_text": btn_txt,
            form_name: form,
        }
    )
    if user_id:
        context.update(
            {
                "staff_user_id": user_id,
            }
        )
    if instance:
        context.update(
            {
                "working_hours_instance": instance,
            }
        )
    if wh_id:
        context.update(
            {
                "working_hours_id": wh_id,
            }
        )
    context.update(
        {
            "today": moscow_now,
        }
    )
    return context


def handle_day_off_form(day_off_form, staff_member):
    """Handle the day off form."""
    if day_off_form.is_valid():
        day_off = day_off_form.save(commit=False)
        day_off.staff_member = staff_member
        day_off.save()
        redirect_url = reverse(
            "user_profile", kwargs={"staff_user_id": staff_member.user.id}
        )
        return json_response(
            "Выходные успешно добавлены", custom_data={"redirect_url": redirect_url}
        )
    else:
        message = "Invalid data:"
        message += get_error_message_in_form(form=day_off_form)
        return json_response(
            message, status=400, success=False, error_code=ErrorCode.INVALID_DATA
        )


def get_error_message_in_form(form):
    """
    Get the error message in a form.
    """
    error_messages = []
    for field, errors in form.errors.items():
        error_messages.append(f"{field}: {','.join(errors)}")
    if len(error_messages) == 3:
        return "Empty fields are not allowed."
    return " ".join(error_messages)


def handle_working_hours_form(
        staff_member, day_of_week, start_time, end_time, add, wh_id=None
):
    # Handle the working hours form.

    # Validate inputs
    if not (staff_member and day_of_week and start_time and end_time):
        return json_response(
            "Invalid data.",
            status=400,
            success=False,
            error_code=ErrorCode.INVALID_DATA,
        )

    # Convert start time and end time to 24-hour format

    # Ensure start time is before end time
    if start_time >= end_time:
        return json_response(
            "Start time must be before end time.",
            status=400,
            success=False,
            error_code=ErrorCode.INVALID_DATA,
        )

    if add:
        # Create new working hours
        if working_hours_exist(day_of_week=day_of_week, staff_member=staff_member):
            return json_response(
                "Выходные уже выбраны.",
                status=400,
                success=False,
                error_code=ErrorCode.WORKING_HOURS_CONFLICT,
            )
        wk = WorkingHours(
            staff_member=staff_member,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
        )
    else:
        # Ensure working_hours_id is provided
        if not wh_id:
            return json_response(
                "Invalid or no working_hours_id provided.",
                status=400,
                success=False,
                error_code=ErrorCode.INVALID_DATA,
            )

        # Get the working hours instance to update
        try:
            wk = WorkingHours.objects.get(pk=wh_id)
            wk.day_of_week = day_of_week
            wk.start_time = start_time
            wk.end_time = end_time
        except WorkingHours.DoesNotExist:
            return json_response(
                "Working hours does not exist.",
                status=400,
                success=False,
                error_code=ErrorCode.WORKING_HOURS_NOT_FOUND,
            )

        # Save working hours
    wk.save()

    # Return success with redirect URL
    redirect_url = (
        reverse("user_profile", kwargs={"staff_user_id": staff_member.user.id})
        if staff_member.user.id
        else reverse("user_profile")
    )
    return json_response(
        "Working hours saved successfully.", custom_data={"redirect_url": redirect_url}
    )


def arhiv_appointment(appt):
    archived_appointment_request = ArchivedAppointmentRequest()

    for field in appt.appointment_request._meta.fields:
        setattr(archived_appointment_request, field.name, getattr(appt.appointment_request, field.name))
    archived_appointment_request.pk = None
    archived_appointment_request.save()

    archived_appointment = ArchivedAppointment()
    for field in appt._meta.fields:
        if field.name != 'appointment_request':
            setattr(archived_appointment, field.name, getattr(appt, field.name))
    archived_appointment.appointment_request = archived_appointment_request
    archived_appointment.pk = None
    archived_appointment.save()
