from django.contrib import admin
from .models import Account, CreditCard, Category, Tag, Transaction, Invoice, CardCharge, InvoicePayment, RecurringTransaction, RecurringCardPurchase

# Register your models here.
@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "user", "active")
    list_filter = ("type", "active")
    search_fields = ("name", "user__username")


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "closing_day", "due_day", "user", "active")
    list_filter = ("active",)
    search_fields = ("name", "brand", "user__username")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "parent", "user")
    list_filter = ("kind",)
    search_fields = ("name", "user__username")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
    search_fields = ("name", "user__username")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "amount", "type", "account", "user", "reconciled")
    list_filter = ("type", "reconciled", "account")
    search_fields = ("description", "user__username")
    date_hierarchy = "date"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("card", "year", "month", "status", "closing_date", "due_date")
    list_filter = ("status", "card")
    search_fields = ("card__name",)


@admin.register(CardCharge)
class CardChargeAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "card", "invoice", "installment_number", "installments_total", "total_amount")
    list_filter = ("card", "invoice")
    search_fields = ("description", "card__name")
    date_hierarchy = "date"


@admin.register(InvoicePayment)
class InvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ("date", "invoice", "account", "amount", "kind")
    list_filter = ("kind", "account")
    date_hierarchy = "date"


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ("description", "account", "type", "amount", "next_date", "active")
    list_filter = ("active", "type")
    search_fields = ("description",)


@admin.register(RecurringCardPurchase)
class RecurringCardPurchaseAdmin(admin.ModelAdmin):
    list_display = ("description", "card", "total_amount", "installments_total", "next_date", "active")
    list_filter = ("active",)
    search_fields = ("description",)
