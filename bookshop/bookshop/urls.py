from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static
from core.views import (
    add_to_cart,
    books_list,
    books_by_genre,
    books_by_author,
    books_by_publisher,
    search_books,
    cart_view,
    home,
    product_detail,
    remove_from_cart,
    checkout,
    order_success,
    stationery_list,
    update_cart_quantity,
    author_detail,
)
from core.views_auth import (
    register_view,
    login_view,
    logout_view,
    profile_view,
    edit_profile,
    add_review,
    add_saved_address,
    delete_saved_address,
    add_payment_card,
    delete_payment_card,
)
from core.views_support import (
    support_chat,
    support_send_message,
    search_faq,
)
from core.views_manager import (
    manager_dashboard,
    manager_orders,
    manager_order_detail,
    manager_products,
    manager_statistics,
    manager_users,
    manager_export_data,
    manager_import_data,
    manager_reports,
    manager_reports_export_csv,
    manager_reports_export_image,
    manager_audit_log,
    manager_audit_log_details,
)
from core.views_admin import (
    admin_export_data,
    admin_import_data,
    admin_reports,
    admin_reports_export_csv,
    admin_reports_export_image,
)
from core.forms import CustomPasswordResetForm

# Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Lexicon Bookshop API",
        default_version='v1',
        description="API для интернет-магазина книг и канцтоваров",
        contact=openapi.Contact(email="lexicon@support.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Основные страницы
    path('', home, name='home'),
    path('books/', books_list, name='books_list'),
    path('books/search/', search_books, name='search_books'),
    path('books/genre/<int:genre_id>/', books_by_genre, name='books_by_genre'),
    path('books/author/<int:author_id>/', books_by_author, name='books_by_author'),
    path('author/<int:author_id>/', author_detail, name='author_detail'),
    path('books/publisher/<int:publisher_id>/', books_by_publisher, name='books_by_publisher'),
    path('stationery/', stationery_list, name='stationery_list'),
    path('products/<str:product_type>/<int:pk>/', product_detail, name='product_detail'),
    path('cart/', cart_view, name='cart_view'),
    path('cart/add/<str:product_type>/<int:pk>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<str:product_type>/<int:pk>/', remove_from_cart, name='remove_from_cart'),
    path('cart/update/<str:product_type>/<int:pk>/', update_cart_quantity, name='update_cart_quantity'),
    path('checkout/', checkout, name='checkout'),
    path('checkout/success/<int:order_id>/', order_success, name='order_success'),

    # Поддержка (только для авторизованных)
    path('support/', support_chat, name='support_chat'),
    path('support/send-message/', support_send_message, name='support_send_message'),
    path('support/search-faq/', search_faq, name='search_faq'),

    # Авторизация
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('profile/review/<int:order_id>/<int:book_id>/', add_review, name='add_review'),
    path('profile/address/add/', add_saved_address, name='add_saved_address'),
    path('profile/address/<int:address_id>/delete/', delete_saved_address, name='delete_saved_address'),
    path('profile/card/add/', add_payment_card, name='add_payment_card'),
    path('profile/card/<int:card_id>/delete/', delete_payment_card, name='delete_payment_card'),
    
    # Сброс пароля
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             form_class=CustomPasswordResetForm,
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt',
             success_url='/password-reset/done/',
             html_email_template_name=None,
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/password-reset/complete/',
             post_reset_login=False,
         ), 
         name='password_reset_confirm'),
    path('password-reset/complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),

    # Панель менеджера
    path('manager/', manager_dashboard, name='manager_dashboard'),
    path('manager/orders/', manager_orders, name='manager_orders'),
    path('manager/orders/<int:order_id>/', manager_order_detail, name='manager_order_detail'),
    path('manager/products/', manager_products, name='manager_products'),
    path('manager/statistics/', manager_statistics, name='manager_statistics'),
    path('manager/users/', manager_users, name='manager_users'),
    path('manager/reports/', manager_reports, name='manager_reports'),
    path('manager/reports/export-csv/', manager_reports_export_csv, name='manager_reports_export_csv'),
    path('manager/reports/export-image/', manager_reports_export_image, name='manager_reports_export_image'),
    path('manager/audit-log/', manager_audit_log, name='manager_audit_log'),
    path('manager/export-data/', manager_export_data, name='manager_export_data'),
    path('manager/import-data/', manager_import_data, name='manager_import_data'),
    path('manager/audit-log/', manager_audit_log, name='manager_audit_log'),

    # Админка - кастомные маршруты должны быть ПЕРЕД admin.site.urls
    path('admin/export-data/', admin_export_data, name='admin_export_data'),
    path('admin/import-data/', admin_import_data, name='admin_import_data'),
    path('admin/reports/', admin_reports, name='admin_reports'),
    path('admin/reports/export-csv/', admin_reports_export_csv, name='admin_reports_export_csv'),
    path('admin/reports/export-image/', admin_reports_export_image, name='admin_reports_export_image'),
    path('admin/', admin.site.urls),
    
    # API
    path('api/', include('core.urls')),

    # Swagger / Redoc
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
