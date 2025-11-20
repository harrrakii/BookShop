from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordResetForm
from django.contrib.auth import get_user_model

from .models import DeliveryOption, Order, PickupPoint, Review, SavedAddress, PaymentCard, Role

User = get_user_model()


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=255, label="ФИО", widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"class": "form-control"}))
    phone = forms.CharField(max_length=30, label="Телефон", widget=forms.TextInput(attrs={"class": "form-control"}))
    fulfillment_type = forms.ChoiceField(
        choices=Order.FulfillmentType.choices,
        label="Способ получения",
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
    )
    delivery_option = forms.ModelChoiceField(
        queryset=DeliveryOption.objects.filter(is_active=True),
        required=False,
        label="Вариант доставки",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    saved_address = forms.ModelChoiceField(
        queryset=SavedAddress.objects.none(),
        required=False,
        label="Сохраненный адрес",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    delivery_city = forms.CharField(max_length=120, required=False, label="Город", widget=forms.TextInput(attrs={"class": "form-control"}))
    delivery_street = forms.CharField(max_length=255, required=False, label="Улица", widget=forms.TextInput(attrs={"class": "form-control"}))
    delivery_building = forms.CharField(max_length=50, required=False, label="Дом", widget=forms.TextInput(attrs={"class": "form-control"}))
    delivery_apartment = forms.CharField(max_length=50, required=False, label="Квартира", widget=forms.TextInput(attrs={"class": "form-control"}))
    delivery_postal_code = forms.CharField(max_length=20, required=False, label="Индекс", widget=forms.TextInput(attrs={"class": "form-control"}))
    delivery_address = forms.CharField(required=False, widget=forms.HiddenInput())
    pickup_point = forms.ModelChoiceField(
        queryset=PickupPoint.objects.filter(is_active=True),
        required=False,
        label="Пункт выдачи",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    payment_card = forms.ModelChoiceField(
        queryset=PaymentCard.objects.none(),
        required=False,
        label="Сохраненная карта",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    new_card_number = forms.CharField(
        max_length=19,
        required=False,
        label="Номер карты",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "1234 5678 9012 3456"}),
    )
    new_cardholder_name = forms.CharField(max_length=255, required=False, label="Имя держателя", widget=forms.TextInput(attrs={"class": "form-control"}))
    new_card_expiry_month = forms.IntegerField(min_value=1, max_value=12, required=False, label="Месяц", widget=forms.NumberInput(attrs={"class": "form-control"}))
    new_card_expiry_year = forms.IntegerField(min_value=2024, max_value=2100, required=False, label="Год", widget=forms.NumberInput(attrs={"class": "form-control"}))
    new_card_cvv = forms.CharField(max_length=4, required=False, label="CVV", widget=forms.TextInput(attrs={"class": "form-control", "type": "password"}))
    comment = forms.CharField(required=False, label="Комментарий к заказу", widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields["saved_address"].queryset = SavedAddress.objects.filter(user=user)
            self.fields["payment_card"].queryset = PaymentCard.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        fulfillment_type = cleaned_data.get("fulfillment_type")
        saved_address = cleaned_data.get("saved_address")
        payment_card = cleaned_data.get("payment_card")

        if fulfillment_type == Order.FulfillmentType.DELIVERY:
            if not saved_address:
                # Проверяем поля нового адреса
                if not cleaned_data.get("delivery_city"):
                    raise forms.ValidationError("Укажите город доставки")
                if not cleaned_data.get("delivery_street"):
                    raise forms.ValidationError("Укажите улицу доставки")
                if not cleaned_data.get("delivery_building"):
                    raise forms.ValidationError("Укажите дом")
            if not cleaned_data.get("delivery_option"):
                raise forms.ValidationError("Выберите вариант доставки")
        elif fulfillment_type == Order.FulfillmentType.PICKUP:
            if not cleaned_data.get("pickup_point"):
                raise forms.ValidationError("Выберите пункт выдачи")

        # Проверка платежной карты
        if not payment_card:
            if not cleaned_data.get("new_card_number"):
                raise forms.ValidationError("Укажите номер карты или выберите сохраненную карту")
            if not cleaned_data.get("new_cardholder_name"):
                raise forms.ValidationError("Укажите имя держателя карты")
            if not cleaned_data.get("new_card_expiry_month") or not cleaned_data.get("new_card_expiry_year"):
                raise forms.ValidationError("Укажите срок действия карты")
            if not cleaned_data.get("new_card_cvv"):
                raise forms.ValidationError("Укажите CVV код")

        # Формируем адрес доставки
        if fulfillment_type == Order.FulfillmentType.DELIVERY:
            if saved_address:
                cleaned_data["delivery_address"] = f"{saved_address.city}, {saved_address.address}"
            else:
                city = cleaned_data.get("delivery_city", "")
                street = cleaned_data.get("delivery_street", "")
                building = cleaned_data.get("delivery_building", "")
                apartment = cleaned_data.get("delivery_apartment", "")
                postal_code = cleaned_data.get("delivery_postal_code", "")
                address_parts = [city, street, building]
                if apartment:
                    address_parts.append(f"кв. {apartment}")
                if postal_code:
                    address_parts.append(f"индекс: {postal_code}")
                cleaned_data["delivery_address"] = ", ".join(filter(None, address_parts))

        return cleaned_data

    def clean_new_card_number(self):
        card_number = self.cleaned_data.get("new_card_number", "").replace(" ", "").replace("-", "")
        if card_number and len(card_number) < 13:
            raise forms.ValidationError("Номер карты должен содержать минимум 13 цифр")
        return card_number


class UserProfileForm(forms.ModelForm):
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Дата рождения",
        help_text="Можно указать только один раз",
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "middle_name", "phone", "avatar", "birth_date")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "middle_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "avatar": forms.FileInput(attrs={"class": "form-control"}),
            "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        labels = {
            "username": "Никнейм",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "middle_name": "Отчество",
            "phone": "Телефон",
            "avatar": "Аватарка",
            "birth_date": "Дата рождения",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Если дата рождения уже установлена, делаем поле только для чтения
        if self.instance and self.instance.birth_date:
            self.fields["birth_date"].widget.attrs["readonly"] = True
            self.fields["birth_date"].help_text = "Дата рождения уже установлена и не может быть изменена"

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get("birth_date")
        # Если у пользователя уже есть дата рождения, не позволяем её изменить
        if self.instance and self.instance.birth_date and birth_date != self.instance.birth_date:
            raise forms.ValidationError("Дата рождения уже установлена и не может быть изменена")
        return birth_date


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "rating": forms.RadioSelect(choices=[(i, i) for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
        labels = {
            "rating": "Оценка",
            "comment": "Комментарий",
        }


class SavedAddressForm(forms.ModelForm):
    class Meta:
        model = SavedAddress
        fields = ("title", "city", "address", "postal_code", "is_default")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "title": "Название адреса",
            "city": "Город",
            "address": "Адрес",
            "postal_code": "Почтовый индекс",
            "is_default": "Использовать по умолчанию",
        }


class PaymentCardForm(forms.ModelForm):
    card_number = forms.CharField(
        max_length=19,
        label="Номер карты",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "1234 5678 9012 3456"}),
    )

    class Meta:
        model = PaymentCard
        fields = ("card_number", "cardholder_name", "expiry_month", "expiry_year", "is_default")
        widgets = {
            "cardholder_name": forms.TextInput(attrs={"class": "form-control"}),
            "expiry_month": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 12}),
            "expiry_year": forms.NumberInput(attrs={"class": "form-control", "min": 2024}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "card_number": "Номер карты",
            "cardholder_name": "Имя держателя",
            "expiry_month": "Месяц",
            "expiry_year": "Год",
            "is_default": "Использовать по умолчанию",
        }

    def clean_card_number(self):
        card_number = self.cleaned_data.get("card_number", "").replace(" ", "").replace("-", "")
        if len(card_number) < 13:
            raise forms.ValidationError("Номер карты должен содержать минимум 13 цифр")
        return card_number

    def save(self, commit=True):
        instance = super().save(commit=False)
        card_number = self.cleaned_data.get("card_number", "").replace(" ", "").replace("-", "")
        instance.card_number_last4 = card_number[-4:]
        if commit:
            instance.save()
        return instance


# Формы для сброса пароля
class CustomPasswordResetForm(PasswordResetForm):
    """Кастомная форма для сброса пароля, работающая с email"""
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email',
            'autocomplete': 'email'
        })
    )
    
    def get_users(self, email):
        """Переопределяем метод для работы с кастомной моделью User"""
        User = get_user_model()
        active_users = User.objects.filter(email__iexact=email, is_active=True)
        return (u for u in active_users if u.has_usable_password())


# Формы для админки
class CustomUserCreationForm(UserCreationForm):
    """Форма для создания пользователя в админке"""
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label="Роль",
        help_text="Выберите роль пользователя. Если не указана, будет установлена роль 'пользователь'"
    )
    
    class Meta:
        model = User
        fields = ("email", "username", "role")
        field_classes = {"email": forms.EmailField, "username": forms.CharField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password1' in self.fields:
            self.fields['password1'].help_text = "Пароль будет захеширован автоматически"
            self.fields['password1'].widget = forms.PasswordInput(attrs={'class': 'vTextField'})
        if 'password2' in self.fields:
            self.fields['password2'].help_text = "Повторите пароль для подтверждения"
            self.fields['password2'].widget = forms.PasswordInput(attrs={'class': 'vTextField'})
        
        # Делаем email обязательным
        if 'email' in self.fields:
            self.fields['email'].required = True
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Присваиваем роль, если она указана
        role = self.cleaned_data.get('role')
        if role:
            user.role = role
        else:
            # Если роль не указана, устанавливаем роль "пользователь" по умолчанию
            try:
                user_role = Role.objects.get(name='пользователь')
                user.role = user_role
            except Role.DoesNotExist:
                # Если роли нет, создаем её
                user_role = Role.objects.create(name='пользователь')
                user.role = user_role
        
        # Устанавливаем права в зависимости от роли
        if user.role:
            role_name_lower = user.role.name.lower()
            if role_name_lower == 'менеджер':
                user.is_staff = True
                user.is_superuser = False
            elif role_name_lower == 'пользователь':
                user.is_staff = False
                user.is_superuser = False
            elif role_name_lower == 'админ':
                user.is_staff = True
                user.is_superuser = True
        
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Форма для редактирования пользователя в админке"""
    class Meta:
        model = User
        fields = "__all__"
        field_classes = {"email": forms.EmailField}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Пароль обрабатывается автоматически через UserChangeForm
        # Он показывает ссылку на изменение пароля, а не поле ввода
        if 'password' in self.fields:
            # Убираем поле password из fieldsets, так как оно обрабатывается отдельно
            password = self.fields.get('password')
            if password:
                password.help_text = password.help_text + " Вы можете изменить пароль <a href=\"../password/\">здесь</a>."
