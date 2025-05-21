from django.urls import path

from .views import admin_chat, chat_view, get_or_create_chatroom

urlpatterns = (
    [
        path("admin_chats/", admin_chat, name="admin_chat"),
        path("start_chat_admin/", get_or_create_chatroom, name="start_chat"),
        path("room/<chatroom_name>", chat_view, name="chatroom")
    ]
)
