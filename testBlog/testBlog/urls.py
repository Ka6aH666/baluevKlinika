from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from . import settings

urlpatterns = (
    [
        path("admin/", admin.site.urls),
        path("", include("mainController.urls")),
        path("auth/", include("mainUser.urls"), name="login"),
        path("appointment/", include("appointment.urls"), name="app-admin"),
        path("chat/", include("r_t_chat.urls"))
    ]
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)
