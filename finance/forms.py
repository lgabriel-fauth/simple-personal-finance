from django import forms
from django.contrib.auth.models import User
from .models import Transaction, Account, Category, CreditCard, Invoice, Tag, RecurringTransaction, RecurringCardPurchase, CardCharge

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["account", "type", "date", "description", "amount", "category", "tags", "reconciled"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["account"].queryset = Account.objects.filter(user=user, active=True)
            self.fields["category"].queryset = Category.objects.filter(user=user)
            self.fields["tags"].queryset = Tag.objects.filter(user=user)
    
    pass

    


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        user = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        # Bloqueia edição do email se confirmado
        try:
            if user and hasattr(user, "profile") and user.profile.email_confirmed:
                self.fields["email"].disabled = True
        except Exception:
            pass

    def clean_email(self):
        email = self.cleaned_data.get("email")
        user = self.instance
        try:
            if hasattr(user, "profile") and user.profile.email_confirmed:
                # mantém o email original se tentar alterar
                return user.email
        except Exception:
            pass
        return email


class CardChargeForm(forms.ModelForm):
    class Meta:
        model = CardCharge
        fields = [
            "card", "date", "description", "total_amount", "category", "tags",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["card"].queryset = CreditCard.objects.filter(user=user, active=True)
            self.fields["category"].queryset = Category.objects.filter(user=user, kind=Category.Kind.EXPENSE)


class StatementFilterForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.none(), label="Conta")
    start_date = forms.DateField(label="De", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(label="Até", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    type = forms.ChoiceField(choices=(("", "Todos"), ("IN", "Entrada"), ("OUT", "Saída")), required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)
    tag = forms.ModelChoiceField(queryset=Tag.objects.none(), required=False)
    reconciled = forms.ChoiceField(choices=(("", "Todos"), ("1", "Conciliado"), ("0", "Não conciliado")), required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["account"].queryset = Account.objects.filter(user=user, active=True)
            self.fields["category"].queryset = Category.objects.filter(user=user)
            self.fields["tag"].queryset = Tag.objects.filter(user=user)
            self.fields["category"].queryset = Category.objects.filter(user=user)


class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = [
            "account", "type", "description", "amount", "category",
            "frequency", "day_of_month", "start_date", "next_date", "active", "end_date",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["account"].queryset = Account.objects.filter(user=user, active=True)
            self.fields["category"].queryset = Category.objects.filter(user=user)


class RecurringCardPurchaseForm(forms.ModelForm):
    class Meta:
        model = RecurringCardPurchase
        fields = [
            "card", "description", "total_amount", "installments_total", "category",
            "frequency", "day_of_month", "next_date", "active", "end_date",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["card"].queryset = CreditCard.objects.filter(user=user, active=True)
            self.fields["category"].queryset = Category.objects.filter(user=user, kind=Category.Kind.EXPENSE)


class TransferForm(forms.Form):
    from_account = forms.ModelChoiceField(queryset=Account.objects.none(), label="De")
    to_account = forms.ModelChoiceField(queryset=Account.objects.none(), label="Para")
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    description = forms.CharField(max_length=200)
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            qs = Account.objects.filter(user=user, active=True)
            self.fields["from_account"].queryset = qs
            self.fields["to_account"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        from_acc = cleaned.get("from_account")
        to_acc = cleaned.get("to_account")
        if from_acc and to_acc and from_acc == to_acc:
            raise forms.ValidationError("Selecione contas diferentes para transferência.")
        return cleaned


class PurchaseForm(forms.Form):
    card = forms.ModelChoiceField(queryset=CreditCard.objects.none(), label="Cartão")
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    description = forms.CharField(max_length=200)
    total_amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01, label="Valor Total")
    installments_total = forms.IntegerField(min_value=1, initial=1, label="Parcelas")
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["card"].queryset = CreditCard.objects.filter(user=user, active=True)
            self.fields["category"].queryset = Category.objects.filter(user=user, kind=Category.Kind.EXPENSE)


class InvoicePaymentForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.none(), label="Conta para pagar", required=False)
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    kind = forms.ChoiceField(choices=(
        ("TOTAL", "Total"),
        ("PARTIAL", "Parcial"),
        ("ADVANCE", "Antecipação"),
        ("DISCOUNT", "Desconto"),
    ))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["account"].queryset = Account.objects.filter(user=user, active=True)
