import shortuuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models


class ChatGroup(models.Model):
    group_name = models.CharField(max_length=128, unique=True, blank=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_groups', blank=True)
    is_private = models.BooleanField(default=False)
    user_online = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="online_in_groups", blank=True)

    def __str__(self):
        return self.group_name

    def save(self, *args, **kwargs):
        if not self.group_name:
            self.group_name = shortuuid.uuid()
        super().save(*args, **kwargs)

    def get_members_full_name(self):
        return ", ".join(member.get_full_name() for member in self.members.all())


class GroupMessage(models.Model):
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE)
    author = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    body = models.CharField(max_length=300, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.body:
            return f'{self.author.username} : {self.body}'

    class Meta:
        ordering = ['-created']
