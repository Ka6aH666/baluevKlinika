from django.urls import include, path

from . import views, views_admin

ajax_urlpatterns = [
    path(
        "available_slots/", views.get_available_slots_ajax, name="available_slots_ajax"
    ),
    path(
        "request_next_available_slot/<int:service_id>/",
        views.get_next_available_date_ajax,
        name="request_next_available_slot",
    ),
    path(
        "request_staff_info/",
        views.get_non_working_days_ajax,
        name="get_non_working_days_ajax",
    ),
    path(
        "request_staff_settings/",
        views.get_calender_settings_for_staff_ajax,
        name="get_calender_settings_for_staff_ajax",
    ),
    path('delete_appointment/',
         views_admin.delete_appointment_ajax,
         name="delete_appointment_ajax"),

    path('fetch_service_list_for_staff/',
         views_admin.fetch_service_list_for_staff,
         name='fetch_service_list_for_staff'),
    path('fetch_user_list/', views_admin.fetch_user_list, name="fetch_user_list"),
    path('fetch_staff_list/', views_admin.fetch_staff_list, name='fetch_staff_list'),

    path('update_appt_min_info/', views_admin.update_appt_min_info, name="update_appt_min_info"),

    path('update_appt_date_time/', views_admin.update_appt_date_time, name="update_appt_date_time"),

    path('is_user_staff_admin/', views_admin.is_user_staff_admin, name="is_user_staff_admin"),
]

admin_urlpatterns = [
    path("", views_admin.show_abilities, name="show_all"),

    path('appointments/<str:response_type>/', views_admin.get_user_appointments, name='get_user_event_type'),
    path('appointments/', views_admin.get_user_appointments, name='get_user_appointments'),
    path('display-appointment/<int:appointment_id>/', views_admin.display_appointment, name='display_appointment'),
    path('delete-appointment/<int:appointment_id>/', views_admin.delete_appointment, name='delete_appointment'),


    # add, remove, show, update service
    path("add-service/", views_admin.add_or_update_service, name="add_service"),
    path("service-list/", views_admin.get_service_list, name="get_service_list"),
    path(
        "update-service/<int:service_id>/",
        views_admin.add_or_update_service,
        name="update_service",
    ),
    path(
        "delete-service/<int:service_id>/",
        views_admin.delete_service,
        name="delete_service",
    ),
    # add, remove, show, update staff member
    path(
        "add-staff-member-info/",
        views_admin.add_staff_member_info,
        name="add_staff_member_info",
    ),
    path("staff-list/", views_admin.get_staff_list, name="get_staff_list"),
    path(
        "update-staff-member/<int:user_id>/",
        views_admin.update_staff_info,
        name="update_staff_other_info",
    ),
    path(
        "remove-staff-member/<int:staff_user_id>/",
        views_admin.remove_staff_member,
        name="remove_staff_member",
    ),
    ###############################
    # show, update, personal info
    path(
        "user-profile/<int:staff_user_id>/",
        views_admin.user_profile,
        name="user_profile",
    ),
    path("user-profile/", views_admin.user_profile, name="user_profile"),
    path(
        "update-user-info/<int:staff_user_id>/",
        views_admin.update_personal_info,
        name="update_user_info",
    ),
    path(
        "update-user-info/", views_admin.update_personal_info, name="update_user_info"
    ),
    # add, update, delete day off
    path(
        "add-day-off/<int:staff_user_id>/", views_admin.add_day_off, name="add_day_off"
    ),
    path(
        "update-day-off/<int:day_off_id>/",
        views_admin.update_day_off,
        name="update_day_off",
    ),
    path(
        "delete-day-off/<int:day_off_id>/",
        views_admin.delete_day_off,
        name="delete_day_off",
    ),
    # add, update, delete working hours
    path(
        "delete-working-hours/<int:working_hours_id>/",
        views_admin.delete_working_hours,
        name="delete_working_hours",
    ),
    path(
        "update-working-hours/<int:working_hours_id>/",
        views_admin.update_working_hours,
        name="update_working_hours",
    ),
    path(
        "add-working-hours/<int:staff_user_id>/",
        views_admin.add_working_hours,
        name="add_working_hours",
    ),
    path(
        "clients-info/",
        views_admin.clients_info,
        name="clients_info",
    ),
    path(
        "edit_calendar_settings/",
        views_admin.edit_calendar_settings,
        name="edit_calendar_settings",
    )
]

urlpatterns = [
    path("services/", views.show_services, name="services"),
    path(
        "request/<int:service_id>/",
        views.appointment_request,
        name="appointment_request",
    ),
    path(
        "request-submit/",
        views.appointment_request_submit,
        name="appointment_request_submit",
    ),
    path(
        "confirm-appt/<int:appointment_request_id>/",
        views.confirm_appt,
        name="confirm_appt",
    ),
    path(
        "thank-you/<int:appointment_id>/",
        views.default_thank_you,
        name="default_thank_you",
    ),
    path("ajax/", include(ajax_urlpatterns)),
    path("app-admin/", include(admin_urlpatterns), name="app-admin"),
]
