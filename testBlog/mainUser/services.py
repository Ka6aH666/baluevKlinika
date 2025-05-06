from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render

from .forms import UserRegisterForm


def handle_user_registration(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # Создаем пользователя
            user = get_user_model().objects.create_user(
                username=form.cleaned_data['username'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            user.social_link_tg = form.cleaned_data['social_link_tg']
            user.social_link_vk = form.cleaned_data['social_link_vk']
            user.phone_number = form.cleaned_data['phone_number']
            user.save()

            # Отправляем сообщение об успешной регистрации
            messages.success(request, "Ваш аккаунт создан. Вы можете войти на сайт.")
            return redirect('login')  # Перенаправляем на страницу входа
        else:
            # Если форма невалидна, возвращаем ее с ошибками
            return render(request, 'mainUser/registration.html', {'form': form})
    else:
        # Если запрос GET, возвращаем пустую форму
        form = UserRegisterForm()
        return render(request, 'mainUser/registration.html', {'form': form})
