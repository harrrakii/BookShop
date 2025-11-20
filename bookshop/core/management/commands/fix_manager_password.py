from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Исправляет пароль для менеджера (хеширует незахешированный пароль)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email менеджера')
        parser.add_argument('--password', type=str, help='Новый пароль (если не указан, будет использован текущий)')

    def handle(self, *args, **options):
        email = options['email']
        new_password = options.get('password')
        
        try:
            user = User.objects.get(email=email)
            self.stdout.write(f'Найден пользователь: {user.email}')
            
            # Проверяем, захеширован ли пароль
            # Если пароль не начинается с известных хешей Django, значит он не захеширован
            password_hash = user.password
            if password_hash and not (password_hash.startswith('pbkdf2_') or 
                                       password_hash.startswith('argon2') or 
                                       password_hash.startswith('bcrypt') or
                                       len(password_hash) < 50):
                self.stdout.write(self.style.WARNING(f'Пароль пользователя {email} не захеширован или имеет неправильный формат'))
                
                if new_password:
                    user.set_password(new_password)
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Пароль для {email} успешно обновлен и захеширован'))
                else:
                    self.stdout.write(self.style.ERROR('Необходимо указать новый пароль через --password'))
                    return
            else:
                if new_password:
                    user.set_password(new_password)
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Пароль для {email} успешно обновлен'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Пароль пользователя {email} уже захеширован правильно'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Пользователь с email {email} не найден'))



