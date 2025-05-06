from django.contrib import admin

from .models import ChatGroup, GroupMessage


@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    list_display = (
        "group_name",
        "is_private",
    )


@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = (
        "group",
        "author",
        "body",
        "created",
    )
