"""
Middleware для отслеживания важных действий пользователей
"""
from django.utils.deprecation import MiddlewareMixin
from .audit import log_action


class AuditMiddleware(MiddlewareMixin):
    """
    Middleware для отслеживания важных действий пользователей
    Отслеживает только определенные URL-паттерны, чтобы не засорять базу
    """
    
    # URL-паттерны, которые нужно отслеживать
    TRACKED_PATHS = [
        '/manager/',  # Все действия в панели менеджера
        '/admin/',  # Все действия в админке
        '/support/',  # Обращения в поддержку
        '/profile/',  # Просмотр профиля
        '/cart/',  # Работа с корзиной
        '/checkout/',  # Оформление заказа
    ]
    
    # Игнорируемые пути (статические файлы, медиа и т.д.)
    IGNORED_PATHS = [
        '/static/',
        '/media/',
        '/favicon.ico',
        '/robots.txt',
    ]
    
    def process_request(self, request):
        """Обрабатывает запрос и логирует важные действия"""
        path = request.path
        
        # Пропускаем игнорируемые пути
        if any(path.startswith(ignored) for ignored in self.IGNORED_PATHS):
            return None
        
        # Отслеживаем только важные пути
        if any(path.startswith(tracked) for tracked in self.TRACKED_PATHS):
            # Определяем тип действия на основе метода и пути
            action = 'view'
            description = f'Просмотр страницы: {path}'
            
            if request.method == 'POST':
                if '/manager/' in path or '/admin/' in path:
                    action = 'config'
                    description = f'Действие администратора: {path}'
                else:
                    action = 'other'
                    description = f'POST запрос: {path}'
            
            # Логируем только для важных действий (не все просмотры)
            # Чтобы не засорять базу, логируем только POST-запросы и действия в админке/панели менеджера
            if request.method == 'POST' or '/manager/' in path or '/admin/' in path:
                log_action(
                    action=action,
                    user=request.user if request.user.is_authenticated else None,
                    request=request,
                    description=description,
                )
        
        return None

