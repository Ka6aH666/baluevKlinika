// Функция для отображения модального окна подтверждения
function showModal(title, message, confirmText, confirmUrl) {
    // Получаем элементы модального окна
    const modalElement = document.getElementById('confirmModal');
    const modalTitle = document.getElementById('confirmModalLabel');
    const modalBody = document.getElementById('confirmModalBody');
    const confirmBtn = document.getElementById('confirmModalButton');

    // Проверяем, существуют ли все элементы
    if (!modalElement || !modalTitle || !modalBody || !confirmBtn) {
        console.error('One or more modal elements not found:', {
            modalElement,
            modalTitle,
            modalBody,
            confirmBtn
        });
        return;
    }

    // Инициализируем модальное окно
    const modal = new bootstrap.Modal(modalElement);

    // Устанавливаем содержимое модального окна
    modalTitle.textContent = title || 'Подтверждение действия';
    modalBody.textContent = message || 'Вы уверены, что хотите выполнить это действие?';
    confirmBtn.textContent = confirmText || 'Подтвердить';

    // Удаляем предыдущие обработчики событий
    confirmBtn.replaceWith(confirmBtn.cloneNode(true));
    const newConfirmBtn = document.getElementById('confirmModalButton');

    // Добавляем новый обработчик для кнопки подтверждения
    newConfirmBtn.addEventListener('click', function () {
        if (confirmUrl) {
            window.location.href = confirmUrl; // Переход по URL
        }
        modal.hide();
    });

    // Показываем модальное окно
    modal.show();
}

// Обработчик для автоматического скрытия сообщений
document.addEventListener('DOMContentLoaded', function () {
    const messageElements = document.querySelectorAll('.alert-dismissible');
    setTimeout(function () {
        messageElements.forEach(function (element) {
            element.style.display = 'none';
        });
    }, 5000);
});