"""
Views для чата поддержки
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.http import require_http_methods
import os

from .models import FAQ, SupportMessage


def support_chat(request):
    """Страница чата поддержки с FAQ и чатом"""
    # Получаем все активные FAQ, сгруппированные по категориям
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'question')
    
    # Группируем по категориям
    faqs_by_category = {}
    for faq in faqs:
        if faq.category not in faqs_by_category:
            faqs_by_category[faq.category] = []
        faqs_by_category[faq.category].append(faq)
    
    # Названия категорий
    category_names = {
        'delivery': 'Доставка',
        'return': 'Возврат',
        'payment': 'Оплата',
        'order': 'Заказ',
        'loyalty': 'Программа лояльности',
        'other': 'Другое',
    }
    
    # Получаем сообщения пользователя (только если авторизован)
    messages_list = None
    if request.user.is_authenticated:
        messages_list = SupportMessage.objects.filter(
            user=request.user
        ).order_by('created_at')
    
    context = {
        'faqs_by_category': faqs_by_category,
        'category_names': category_names,
        'messages_list': messages_list,
    }
    
    return render(request, 'support/chat.html', context)


@login_required
@require_http_methods(["POST"])
def support_send_message(request):
    """Отправка сообщения в поддержку - только для авторизованных пользователей"""
    message_text = request.POST.get('message', '').strip()
    attachment_file = request.FILES.get('attachment')
    
    # Валидация
    if not message_text:
        messages.error(request, 'Пожалуйста, введите ваше сообщение')
        return redirect('support_chat')
    
    # Валидация файла
    if attachment_file:
        # Проверяем размер (максимум 10MB)
        if attachment_file.size > 10 * 1024 * 1024:
            messages.error(request, 'Размер файла не должен превышать 10MB')
            return redirect('support_chat')
        
        # Проверяем расширение файла
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx', '.txt', '.zip', '.rar']
        file_ext = os.path.splitext(attachment_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            messages.error(request, f'Неподдерживаемый тип файла. Разрешенные: {", ".join(allowed_extensions)}')
            return redirect('support_chat')
    
    # Создаем сообщение
    support_message = SupportMessage.objects.create(
        user=request.user,
        name=request.user.get_full_name() or request.user.username or request.user.email,
        email=request.user.email,
        message=message_text,
        attachment=attachment_file,
        status='new'
    )
    
    messages.success(
        request,
        'Ваше сообщение отправлено! Мы свяжемся с вами в ближайшее время.'
    )
    
    return redirect('support_chat')


def search_faq(request):
    """Поиск по FAQ (AJAX)"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'support/faq_results.html', {'faqs': []})
    
    # Поиск по вопросу и ответу
    faqs = FAQ.objects.filter(
        Q(question__icontains=query) | Q(answer__icontains=query),
        is_active=True
    ).order_by('order', 'question')[:10]
    
    return render(request, 'support/faq_results.html', {'faqs': faqs})



