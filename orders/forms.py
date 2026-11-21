from django import forms

from accounts.models import CustomerProfile
from .models import Order


class CheckoutForm(forms.Form):
    checkout_token = forms.UUIDField(widget=forms.HiddenInput)
    full_name = forms.CharField(max_length=160, min_length=2)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, min_length=5)
    address = forms.CharField(max_length=255, min_length=5)
    city = forms.CharField(max_length=100, min_length=2)
    region = forms.CharField(max_length=100, min_length=2)
    country = forms.CharField(max_length=100, initial="Ghana")
    payment_method = forms.ChoiceField(choices=Order.PaymentMethod.choices, initial=Order.PaymentMethod.CASH_ON_DELIVERY, widget=forms.RadioSelect)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not self.is_bound:
            profile = CustomerProfile.objects.filter(user=user).first()
            self.initial.update({
                "full_name": user.get_full_name(), "email": user.email,
                "phone": profile.phone if profile else "", "address": profile.address if profile else "",
                "city": profile.city if profile else "", "region": profile.region if profile else "",
                "country": profile.country if profile else "Ghana",
            })

    def clean_payment_method(self):
        method = self.cleaned_data["payment_method"]
        if method != Order.PaymentMethod.CASH_ON_DELIVERY:
            raise forms.ValidationError("Cash on delivery is the only available payment method.")
        return method
