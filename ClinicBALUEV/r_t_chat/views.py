from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .decorators import require_superuser
from .forms import ChatmessageCreateForm
from .models import ChatGroup


@login_required
@require_superuser
def admin_chat(request):
    """Страница администратора со списком всех пользователей"""
    chat_groups = ChatGroup.objects.filter(is_private=True)

    return render(request, "admin_chats.html", {"chat_groups": chat_groups})


@login_required
def get_or_create_chatroom(request):
    other_user = get_user_model().objects.filter(is_superuser=True).first()

    chat = ChatGroup.objects.filter(
        is_private=True,
        members=request.user
    ).filter(members=other_user).first()

    if chat:
        return redirect('chatroom', chat.group_name)

    chat = ChatGroup.objects.create(is_private=True)
    chat.members.add(request.user, other_user)
    chat.save()

    return redirect('chatroom', chat.group_name)


@login_required
def chat_view(request, chatroom_name):
    chat_group = get_object_or_404(ChatGroup, group_name=chatroom_name)
    chat_messages = chat_group.groupmessage_set.all().order_by("created")
    form = ChatmessageCreateForm()

    if request.user in chat_group.members.all():
        other_user = chat_group.members.exclude(id=request.user.id).first()
    else:
        raise Http404()

    if request.htmx:
        form = ChatmessageCreateForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.author = request.user
            message.group = chat_group
            message.save()
            context = {
                'message': message,
                'user': request.user
            }
            return render(request, "partials/chat_p.html", context)

    context = {
        'chat_messages': chat_messages,
        'form': form,
        'other_user': other_user,
        'chatroom_name': chatroom_name,
        'chat_group': chat_group
    }

    return render(request, "chat.html", context=context)
