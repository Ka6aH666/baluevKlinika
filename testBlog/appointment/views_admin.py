import json
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .decorators import (require_ajax, require_staff_or_superuser,
                         require_superuser, require_user_authenticated)
from .forms import (CalendarSettingsForm, PersonalInformationForm, ServiceForm,
                    StaffAppointmentInformationForm, StaffMemberForm)
from .models import (Appointment, ArchivedAppointment, DayOff, Service,
                     StaffMember, WorkingHours)
from .services import (arhiv_appointment, check_exists_calander_settings,
                       create_new_appt_from_calender_modal,
                       fetch_user_appointments,
                       handle_entity_management_request,
                       prepare_appointment_display_data,
                       prepare_user_profile_data, save_appt_date_time,
                       update_existing_appointment,
                       update_personal_info_service)
from .utils.error_codes import ErrorCode
from .utils.json_context import (convert_appointment_to_json,
                                 get_generic_context,
                                 get_generic_context_with_extra,
                                 handle_unauthorized_response, json_response)
from .utils.permissions import (check_extensive_permissions, check_permissions,
                                has_permission_to_delete_appointment)


@require_user_authenticated
@require_staff_or_superuser
def add_or_update_service(request, service_id=None):
    if service_id:
        service = get_object_or_404(Service, pk=service_id)
        page_title = _("View service")
        btn_text = _("Save")
    else:
        service = None
        page_title = _("Добавить услугу")
        btn_text = _("Add")
    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            if service:
                messages.success(request, _("Service saved successfully"))
            else:
                messages.success(request,
                                 _("The service has been successfully added. Don't forget to select the master providing the service"))
            return redirect("get_service_list" if service else "add_service")
    else:
        form = ServiceForm(instance=service)
    context = {
        "page_title": page_title,
        "btn_text": btn_text,
        "form": form,
    }
    return render(request, "administration/manage_service.html", context)


@require_user_authenticated
@require_staff_or_superuser
def get_service_list(request):
    services = Service.objects.all()
    context = {"services": services}
    return render(request, "administration/service_list.html", context=context)


@require_user_authenticated
@require_staff_or_superuser
def show_abilities(request):
    return render(request, "administration/manege_all.html")


@require_user_authenticated
@require_staff_or_superuser
def delete_service(request, service_id):
    service = get_object_or_404(Service, pk=service_id)
    try:
        service.delete()
        messages.success(request, _("Service removed"))
        return redirect("get_service_list")
    except ProtectedError:
        messages.info(request, _("To delete a service, you must manually delete all records for this service"
                                 " and remove it from the master's offered services"))
    return redirect("get_service_list")


@require_user_authenticated
@require_staff_or_superuser
def add_staff_member_info(request):
    if request.method == "POST":
        form = StaffMemberForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            user.is_staff = True
            user.save()
            form.save()
            messages.success(request, _("The employee has been successfully created"))
            return redirect("get_staff_list")
    else:
        form = StaffMemberForm()
    context = {
        "page_title": "Создание сотрудника",
        "btn_text": "Добавить",
        "form": form,
    }
    return render(request, "administration/manage_staff.html", context=context)


@require_user_authenticated
@require_staff_or_superuser
def update_personal_info(request, staff_user_id=None, response_type="html"):
    if not check_permissions(staff_user_id=staff_user_id, user=request.user):
        message = "Вы можете изменять только собственную персональную информацию"
        return handle_unauthorized_response(request, message, response_type)

    if request.method == "POST":
        user, is_valid, error_message = update_personal_info_service(
            staff_user_id, request.POST, request.user
        )
        if is_valid:
            return redirect("user_profile")
        else:
            messages.error(request, error_message)
            return redirect("update_personal_info")

    if staff_user_id:
        user = get_user_model().objects.get(pk=staff_user_id)
    else:
        user = request.user

    form = PersonalInformationForm(
        initial={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
        user=user,
    )

    context = get_generic_context_with_extra(
        request=request, extra={"form": form, "btn_text": "Сохранить"}
    )
    return render(request, "administration/manage_staff_personal_info.html", context)


@require_user_authenticated
@require_staff_or_superuser
def get_staff_list(request):
    staff_members = StaffMember.objects.all()
    context = {"staff_members": staff_members}
    return render(request, "administration/staff_list.html", context=context)


@require_user_authenticated
@require_staff_or_superuser
def remove_staff_member(request, staff_user_id, response_type="html"):
    if not check_permissions(staff_user_id, request.user):
        message = "Вы не можете удалить чужой профиль"
        return handle_unauthorized_response(request, message, response_type)

    staff_member = get_object_or_404(StaffMember, user_id=staff_user_id)
    staff_member.delete()
    user = get_user_model().objects.get(pk=staff_user_id)
    user.is_staff = False
    user.save()
    messages.success(request, "Работник успешно удален!")
    return redirect("get_staff_list")


@require_user_authenticated
@require_staff_or_superuser
def user_profile(request, staff_user_id=None):
    data = prepare_user_profile_data(request.user, staff_user_id)
    context = get_generic_context_with_extra(
        request=request, extra=data["extra_context"]
    )
    template = data["template"]
    return render(request, template, context)


@require_user_authenticated
@require_staff_or_superuser
def update_staff_info(request, user_id=None, response_type="html"):
    if not check_permissions(staff_user_id=user_id, user=request.user):
        message = "Вы можете изменять только собственную информацию приема"
        return handle_unauthorized_response(request, message, response_type)

    staff_member = StaffMember.objects.get(user=user_id)

    if request.method == "POST":
        form = StaffAppointmentInformationForm(request.POST, instance=staff_member)
        if form.is_valid():
            form.save()
            if user_id:
                return redirect("user_profile", staff_user_id=user_id)
            return redirect("user_profile")
    else:
        form = StaffAppointmentInformationForm(instance=staff_member)
    context = {
        "page_title": "Персональная информация",
        "btn_text": "Сохранить",
        "form": form,
    }
    return render(request, "administration/manage_staff.html", context=context)


@require_user_authenticated
@require_staff_or_superuser
def add_day_off(request, staff_user_id=None, response_type="html"):
    if not check_permissions(staff_user_id, request.user):
        message = "Вы можете добавлять только свои собственные выходные дни."
        return handle_unauthorized_response(request, message, response_type)

    staff_member = StaffMember.objects.get(user_id=staff_user_id)
    return handle_entity_management_request(
        request, staff_member, entity_type="day_off"
    )


@require_user_authenticated
@require_staff_or_superuser
def update_day_off(request, day_off_id, staff_user_id=None, response_type="html"):
    day_off = DayOff.objects.get(pk=day_off_id)
    if not day_off:
        if response_type == "json":
            return json_response(
                "Day off does not exist.",
                status=404,
                success=False,
                error_code=ErrorCode.DAY_OFF_NOT_FOUND,
            )
        else:
            context = get_generic_context(request=request)
            return render(
                request, "error_pages/404_not_found.html", context=context, status=404
            )
    if not check_extensive_permissions(request.user.id, request.user, day_off):
        message = _("You can only update your own days off.")
        return handle_unauthorized_response(request, message, response_type)
    staff_user_id = staff_user_id or request.user.pk
    staff_member = StaffMember.objects.get(user_id=staff_user_id)
    return handle_entity_management_request(
        request, staff_member, entity_type="day_off", instance=day_off
    )


@require_user_authenticated
@require_staff_or_superuser
def delete_day_off(request, day_off_id, response_type="html"):
    day_off = get_object_or_404(DayOff, pk=day_off_id)
    if not check_extensive_permissions(request.user.id, request.user, day_off):
        message = _("You can only delete your own days off.")
        return handle_unauthorized_response(request, message, response_type)
    day_off.delete()
    messages.success(request, "Выходные успешно удалены!")
    return redirect("user_profile", staff_user_id=request.user.id)


@require_user_authenticated
@require_staff_or_superuser
def add_working_hours(request, staff_user_id=None, response_type="html"):
    if not check_permissions(staff_user_id, request.user):
        message = "Вы можете добавлять только свои собственные рабочие часы."
        return handle_unauthorized_response(request, message, response_type)

    staff_user_id = staff_user_id or request.user.pk
    staff_user_id = staff_user_id if staff_user_id else request.user.pk

    staff_member = StaffMember.objects.get(user_id=staff_user_id)
    return handle_entity_management_request(
        request=request,
        staff_member=staff_member,
        staff_user_id=staff_user_id,
        entity_type="working_hours",
    )


@require_user_authenticated
@require_staff_or_superuser
def update_working_hours(
        request, working_hours_id, staff_user_id=None, response_type="html"
):
    working_hours = WorkingHours.objects.get(pk=working_hours_id)
    if not working_hours:
        if response_type == "json":
            return json_response(
                "Working hours does not exist.",
                status=404,
                success=False,
                error_code=ErrorCode.WORKING_HOURS_NOT_FOUND,
            )
        else:
            context = get_generic_context(request=request)
            return render(request, "error_pages/404_not_found.html", context=context)
    if not check_extensive_permissions(request.user.id, request.user, working_hours):
        message = _("You can only update your own working hours.")
        return handle_unauthorized_response(request, message, response_type)
    staff_user_id = staff_user_id or request.user.pk
    staff_member = get_object_or_404(
        StaffMember, user_id=staff_user_id or request.user.id
    )
    return handle_entity_management_request(
        request=request,
        staff_member=staff_member,
        add=False,
        instance_id=working_hours_id,
        staff_user_id=staff_user_id,
        entity_type="working_hours",
        instance=working_hours,
    )


@require_user_authenticated
@require_staff_or_superuser
def delete_working_hours(request, working_hours_id, response_type="html"):
    working_hours = get_object_or_404(WorkingHours, pk=working_hours_id)
    if not check_extensive_permissions(request.user.id, request.user, working_hours):
        message = _("You can only delete your own working hours.")
        return handle_unauthorized_response(request, message, response_type)
    working_hours.delete()
    messages.success(request, "Рабочие часы успешно удалены!")
    return redirect("user_profile", staff_user_id=request.user.id)


@require_user_authenticated
@require_staff_or_superuser
def get_user_appointments(request, response_type='html'):
    appointments = fetch_user_appointments(request.user)
    appointments_json = convert_appointment_to_json(request, appointments)

    if response_type == 'json':
        return json_response("Successfully fetched appointments.", custom_data={'appointments': appointments_json},
                             safe=False)

    # Render the HTML template
    extra_context = {
        'appointments': json.dumps(appointments_json),
    }
    context = get_generic_context_with_extra(request=request, extra=extra_context)
    # if appointment is empty and user doesn't have a staff-member instance, put a message
    # it's not clean
    if not appointments and not StaffMember.objects.filter(
            user=request.user).exists() and not request.user.is_superuser:
        messages.error(request, "User doesn't have a staff member instance. Please contact the administrator.")
    return render(request, 'administration/staff_index.html', context)


@require_user_authenticated
@require_staff_or_superuser
def display_appointment(request, appointment_id):
    appointment, page_title, error_message, status_code = prepare_appointment_display_data(request.user, appointment_id)

    if error_message:
        context = get_generic_context(request=request)
        return render(request, 'error_pages/404_not_found.html', context=context, status=status_code)
    # If everything is okay, render the HTML template.
    extra_context = {
        'appointment': appointment,
        'page_title': page_title,
    }
    context = get_generic_context_with_extra(request=request, extra=extra_context)
    return render(request, 'administration/display_appointment.html', context)


@require_user_authenticated
@require_staff_or_superuser
def delete_appointment_ajax(request):
    data = json.loads(request.body)
    appointment_id = data.get("appointment_id")
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    if not has_permission_to_delete_appointment(request.user, appointment):
        message = _("You can only delete your own appointments.")
        return json_response(message, status=403, success=False, error_code=ErrorCode.NOT_AUTHORIZED)
    arhiv_appointment(appointment)
    appointment.appointment_request.delete()
    appointment.delete()
    return json_response("Запись отправлена в архив")


@require_user_authenticated
@require_staff_or_superuser
def fetch_service_list_for_staff(request):
    appointment_id = request.GET.get('appointmentId')
    staff_id = request.GET.get('staff_member')
    if appointment_id:
        # Fetch services for a specific appointment (edit mode)
        if request.user.is_superuser:
            appointment = Appointment.objects.get(id=appointment_id)
            staff_member = appointment.get_staff_member()
        else:
            staff_member = StaffMember.objects.get(user=request.user)
            # Ensure the staff member is associated with this appointment
            if not Appointment.objects.filter(id=appointment_id,
                                              appointment_request__staff_member=staff_member).exists():
                return json_response(_("You do not have permission to access this appointment."), status_code=403)
        services = list(staff_member.get_services_offered().values('id', 'name'))
    elif staff_id:
        # Fetch services for the specified staff member (new mode based on staff member selection)
        staff_member = get_object_or_404(StaffMember, id=staff_id)
        services = list(staff_member.get_services_offered().values('id', 'name'))
    else:
        # Fetch all services for the staff member (create mode)
        try:
            staff_member = StaffMember.objects.get(user=request.user)
            services = list(staff_member.get_services_offered().values('id', 'name'))
        except StaffMember.DoesNotExist:
            if not request.user.is_superuser:
                return json_response(_("You're not a staff member. Can't perform this action !"), status=400,
                                     success=False)
            else:
                services = list(Service.objects.all().values('id', 'name'))

    if len(services) == 0:
        return json_response(_("No services offered by this staff member."), status=404, success=False,
                             error_code=ErrorCode.SERVICE_NOT_FOUND)
    return json_response(_("Successfully fetched services."), custom_data={'services_offered': services})


@require_user_authenticated
@require_superuser
def fetch_staff_list(request):
    staff_members = StaffMember.objects.all()
    staff_data = []
    for staff in staff_members:
        staff_data.append({
            'id': staff.id,
            'name': staff.get_staff_member_name(),
        })
    return json_response("Successfully fetched staff members.", custom_data={'staff_members': staff_data}, safe=False)


@require_user_authenticated
@require_staff_or_superuser
def fetch_user_list(request):
    user_list = get_user_model().objects.filter(is_staff=False)
    user_data = []
    for user in user_list:
        user_data.append({
            'id': user.id,
            'name': user.get_full_name(),
        })
    return json_response("Successfully fetched users.", custom_data={'user_list': user_data}, safe=False)


@require_user_authenticated
@require_staff_or_superuser
@require_ajax
@require_POST
def update_appt_min_info(request):
    data = json.loads(request.body)
    is_creating = data.get('isCreating', False)

    if is_creating:
        # Logic for creating a new appointment
        return create_new_appt_from_calender_modal(data, request)
    else:
        # Logic for updating an existing appointment
        return update_existing_appointment(data, request)


@require_user_authenticated
@require_staff_or_superuser
@require_ajax
@require_POST
def update_appt_date_time(request):
    data = json.loads(request.body)

    # Extracting the data
    start_time = data.get("start_time")
    appt_date = data.get("date")
    appointment_id = data.get("appointment_id")

    # save the data
    try:
        appt = save_appt_date_time(start_time, appt_date, appointment_id, request)
    except Appointment.DoesNotExist:
        return json_response(_("Appointment does not exist."), status=404, success=False,
                             error_code=ErrorCode.APPOINTMENT_NOT_FOUND)
    except ValidationError as e:
        return json_response(e.message, status=400, success=False)
    return json_response(_("Appointment updated successfully."), custom_data={'appt': appt.id})


@require_user_authenticated
@require_staff_or_superuser
def is_user_staff_admin(request):
    user = request.user
    try:
        StaffMember.objects.get(user=user)
        return json_response(_("User is a staff member."), custom_data={'is_staff_admin': True})
    except StaffMember.DoesNotExist:
        # if superuser, all rights are granted even if not a staff member
        if not user.is_superuser:
            return json_response(_("User is not a staff member."), custom_data={'is_staff_admin': False})
        return json_response(_("User is a superuser."), custom_data={'is_staff_admin': True})


@require_user_authenticated
@require_staff_or_superuser
def delete_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    arhiv_appointment(appointment)
    appointment.appointment_request.delete()
    appointment.delete()
    return redirect('get_user_appointments')


def clients_info(request):
    clients = get_user_model().objects.filter(is_staff=False)
    appt = ArchivedAppointment.objects.all()
    context = {
        'clients': clients,
        'appt': appt,
    }
    return render(request, 'administration/clients.html', context=context)


@require_user_authenticated
@require_staff_or_superuser
def edit_calendar_settings(request):
    _, settings = check_exists_calander_settings(request)

    if request.method == "POST":
        form = CalendarSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            return redirect("edit_calendar_settings")
    else:
        form = CalendarSettingsForm(instance=settings)

    start_date = date.today()
    end_date = settings.get_end_date() if settings else None

    return render(request, "administration/calendar_settings_form.html", {"form": form, "start_date": start_date,
                                                                          "end_date": end_date})
