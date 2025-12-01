from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date
import calendar

# Create your models here.

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Account(TimeStampedModel):
    class AccountType(models.TextChoices):
        BANK = "BANK", "Banco"
        WALLET = "WALLET", "Carteira"
        INVEST = "INVEST", "Investimento"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=AccountType.choices, default=AccountType.BANK)
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="BRL")
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class CreditCard(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50, blank=True)
    limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    closing_day = models.PositiveSmallIntegerField(help_text="Dia do fechamento da fatura (1-28)")
    due_day = models.PositiveSmallIntegerField(help_text="Dia do vencimento da fatura (1-28)")
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class Category(TimeStampedModel):
    class Kind(models.TextChoices):
        INCOME = "INCOME", "Receita"
        EXPENSE = "EXPENSE", "Despesa"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)

    class Meta:
        unique_together = ("user", "name")
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class Tag(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Transaction(TimeStampedModel):
    class TxType(models.TextChoices):
        INCOME = "IN", "Entrada"
        OUTCOME = "OUT", "Saída"
        TRANSFER = "TRX", "Transferência"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=3, choices=TxType.choices)
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    reconciled = models.BooleanField(default=False)
    transfer_key = models.CharField(max_length=36, blank=True, help_text="Par para transferências")

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} - {self.description} ({self.amount})"


class Invoice(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberta"
        CLOSED = "CLOSED", "Fechada"
        PAID = "PAID", "Paga"
        PARTIAL = "PARTIAL", "Parcial"

    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name="invoices")
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    closing_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    class Meta:
        unique_together = ("card", "year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.card.name} {self.year}-{self.month:02d}"

    def total_charges(self):
        agg = self.charges.aggregate(s=models.Sum("total_amount"))
        return agg.get("s") or 0

    def total_payments(self):
        agg = self.payments.aggregate(s=models.Sum("amount"))
        return agg.get("s") or 0

    def balance(self):
        return (self.total_charges() or 0) - (self.total_payments() or 0)

    @staticmethod
    def assign_invoice_for(card: "CreditCard", purchase_date: date):
        y = purchase_date.year
        m = purchase_date.month
        # Usa dia de fechamento efetivo do mês (limita ao último dia do mês)
        from calendar import monthrange
        eff_close = min(card.closing_day, monthrange(y, m)[1])
        # Compras no dia de fechamento (ou após) pertencem à fatura do próximo mês
        if purchase_date.day >= eff_close:
            if m == 12:
                y += 1
                m = 1
            else:
                m += 1
        inv, _ = Invoice.objects.get_or_create(card=card, year=y, month=m)
        # Define datas de fechamento/vencimento padrão
        try:
            inv.closing_date = date(y, m, min(card.closing_day, 28))
        except Exception:
            inv.closing_date = None
        # Vencimento no mês seguinte ao mês da fatura
        vy, vm = (y + 1, 1) if m == 12 else (y, m + 1)
        try:
            inv.due_date = date(vy, vm, min(card.due_day, 28))
        except Exception:
            inv.due_date = None
        inv.save()
        return inv

    def next_invoice(self):
        y, m = self.year, self.month
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
        inv, _ = Invoice.objects.get_or_create(card=self.card, year=y, month=m)
        # Preenche datas padrão se necessário
        try:
            inv.closing_date = date(y, m, min(self.card.closing_day, 28))
        except Exception:
            inv.closing_date = None
        vy, vm = (y + 1, 1) if m == 12 else (y, m + 1)
        try:
            inv.due_date = date(vy, vm, min(self.card.due_day, 28))
        except Exception:
            inv.due_date = None
        inv.save()
        return inv


class CardCharge(TimeStampedModel):
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE, related_name="charges")
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="charges")
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=200)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    installment_number = models.PositiveIntegerField(default=1)
    installments_total = models.PositiveIntegerField(default=1)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.description} ({self.installment_number}/{self.installments_total})"

    def save(self, *args, **kwargs):
        old_invoice = None
        if self.pk:
            try:
                old = CardCharge.objects.select_related("invoice").get(pk=self.pk)
                old_invoice = old.invoice
            except CardCharge.DoesNotExist:
                pass
        # Garante fatura correta baseada em card+date
        if self.card_id and self.date:
            inv = Invoice.assign_invoice_for(self.card, self.date)
            if inv.status == Invoice.Status.CLOSED:
                inv = inv.next_invoice()
            self.invoice = inv
        super().save(*args, **kwargs)
        # Remove fatura antiga se tiver ficado vazia
        if old_invoice and (not self.invoice_id or old_invoice.pk != self.invoice_id):
            if not old_invoice.charges.exists() and not old_invoice.payments.exists():
                try:
                    old_invoice.delete()
                except Exception:
                    pass

    def post(self, *args, **kwargs):
        # Limpa relações M2M antes de excluir o lançamento
        try:
            self.tags.clear()
        except Exception:
            pass
        return super().delete(*args, **kwargs)


class InvoicePayment(TimeStampedModel):
    class Kind(models.TextChoices):
        TOTAL = "TOTAL", "Total"
        PARTIAL = "PARTIAL", "Parcial"
        ADVANCE = "ADVANCE", "Antecipação"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="invoice_payments")
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.TOTAL)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"Pagamento {self.amount} em {self.date}"


class RecurringTransaction(TimeStampedModel):
    class Frequency(models.TextChoices):
        MONTHLY = "MONTHLY", "Mensal"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    type = models.CharField(max_length=3, choices=Transaction.TxType.choices)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTHLY)
    day_of_month = models.PositiveSmallIntegerField(default=1)
    next_date = models.DateField(default=timezone.now)
    active = models.BooleanField(default=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-next_date", "-id"]

    def __str__(self):
        return f"{self.get_frequency_display()} {self.description}"

    def generate_next(self):
        if not self.active:
            return None
        nd = self.next_date
        if self.end_date and nd > self.end_date:
            return None
        tx = Transaction.objects.create(
            user=self.user,
            account=self.account,
            type=self.type,
            date=nd,
            description=self.description,
            amount=self.amount,
            category=self.category,
        )
        # advance month
        y = nd.year + (nd.month // 12)
        m = 1 if nd.month == 12 else nd.month + 1
        d = min(self.day_of_month, 28)
        self.next_date = date(y, m, d)
        self.save(update_fields=["next_date"])
        return tx


class RecurringCardPurchase(TimeStampedModel):
    class Frequency(models.TextChoices):
        MONTHLY = "MONTHLY", "Mensal"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    installments_total = models.PositiveIntegerField(default=1)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.MONTHLY)
    day_of_month = models.PositiveSmallIntegerField(default=1)
    next_date = models.DateField(default=timezone.now)
    active = models.BooleanField(default=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-next_date", "-id"]

    def __str__(self):
        return f"{self.get_frequency_display()} {self.description}"

    def generate_next(self):
        if not self.active:
            return None
        nd = self.next_date
        if self.end_date and nd > self.end_date:
            return None
        inv = Invoice.assign_invoice_for(self.card, nd)
        if inv.status == Invoice.Status.CLOSED:
            inv = inv.next_invoice()
        # cria parcelas a partir da data base nd
        from decimal import Decimal
        per_parcel = (self.total_amount / self.installments_total).quantize(Decimal("0.01")) if self.installments_total > 1 else self.total_amount
        for i in range(1, self.installments_total + 1):
            cy = nd.year + ((nd.month - 1 + (i - 1)) // 12)
            cm = ((nd.month - 1 + (i - 1)) % 12) + 1
            last_day = calendar.monthrange(cy, cm)[1]
            cday = min(nd.day, last_day)
            cdate = date(cy, cm, cday)
            inv_i = Invoice.assign_invoice_for(self.card, cdate)
            if inv_i.status == Invoice.Status.CLOSED:
                inv_i = inv_i.next_invoice()
            CardCharge.objects.create(
                card=self.card,
                invoice=inv_i,
                date=cdate,
                description=self.description,
                total_amount=per_parcel,
                installment_number=i,
                installments_total=self.installments_total,
                category=self.category,
            )
        # advance month for next recurrence
        y = nd.year + (nd.month // 12)
        m = 1 if nd.month == 12 else nd.month + 1
        last_day_next = calendar.monthrange(y, m)[1]
        d = min(self.day_of_month, last_day_next)
        self.next_date = date(y, m, d)
        self.save(update_fields=["next_date"])
        return inv
