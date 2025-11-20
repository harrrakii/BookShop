"""
Тестовая команда для проверки отправки email
Использование: python manage.py test_email user@example.com
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Тестовая отправка email для проверки настроек'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email адрес для тестового письма')

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write(f'Настройки email:')
        self.stdout.write(f'  EMAIL_BACKEND: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'  EMAIL_HOST: {settings.EMAIL_HOST}')
        self.stdout.write(f'  EMAIL_PORT: {settings.EMAIL_PORT}')
        self.stdout.write(f'  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER or "(не указан)"}')
        self.stdout.write(f'  DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write('')
        
        try:
            send_mail(
                subject='Тестовое письмо от Lexicon',
                message='Это тестовое письмо для проверки настроек email.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Письмо успешно отправлено на {email}'))
            self.stdout.write('Проверьте папку "Входящие" и "Спам" в вашем почтовом ящике.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка при отправке письма: {str(e)}'))
            self.stdout.write('')
            self.stdout.write('Возможные причины:')
            self.stdout.write('1. Неправильные настройки SMTP в .env файле')
            self.stdout.write('2. Неверные учетные данные (EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)')
            self.stdout.write('3. Для Gmail нужно использовать "Пароль приложения" вместо обычного пароля')
            self.stdout.write('4. Firewall или антивирус блокируют SMTP подключение')
            self.stdout.write('')
            self.stdout.write('Для Gmail:')
            self.stdout.write('1. Включите двухфакторную аутентификацию')
            self.stdout.write('2. Создайте "Пароль приложения" в настройках аккаунта Google')
            self.stdout.write('3. Используйте этот пароль в EMAIL_HOST_PASSWORD')



