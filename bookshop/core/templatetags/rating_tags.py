from django import template

register = template.Library()


@register.filter
def rating_stars(rating):
    """Возвращает список звезд для рейтинга (0-5)"""
    rating = float(rating) if rating else 0.0
    stars = []
    for i in range(1, 6):
        if i <= rating:
            stars.append('filled')
        else:
            stars.append('empty')
    return stars


@register.filter
def int_rating(rating):
    """Преобразует рейтинг в целое число"""
    try:
        return int(float(rating))
    except (ValueError, TypeError):
        return 0



