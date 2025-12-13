from rest_framework import serializers

from finance.models import (
    Account,
    CreditCard,
    Category,
    Tag,
    Transaction,
    Invoice,
    CardCharge,
    InvoicePayment,
    RecurringTransaction,
    RecurringCardPurchase,
)


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'id', 'created_at', 'updated_at',
            'name', 'type', 'initial_balance', 'currency', 'active',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreditCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditCard
        fields = [
            'id', 'created_at', 'updated_at',
            'name', 'brand', 'limit', 'closing_day', 'due_day', 'active',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id', 'created_at', 'updated_at',
            'name', 'parent', 'kind',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            'id', 'created_at', 'updated_at',
            'name',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            'id', 'created_at', 'updated_at',
            'account', 'type', 'date', 'description', 'amount', 'category', 'tags',
            'reconciled', 'transfer_key', 'recurring_transaction',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    total_charges = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_payments = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'created_at', 'updated_at',
            'card', 'year', 'month', 'closing_date', 'due_date', 'status',
            'total_charges', 'total_payments', 'balance',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['total_charges'] = instance.total_charges()
        data['total_payments'] = instance.total_payments()
        data['balance'] = instance.balance()
        return data


class CardChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardCharge
        fields = [
            'id', 'created_at', 'updated_at',
            'card', 'invoice', 'date', 'description', 'total_amount',
            'installment_number', 'installments_total', 'category', 'tags',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoicePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoicePayment
        fields = [
            'id', 'created_at', 'updated_at',
            'invoice', 'account', 'date', 'amount', 'kind',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecurringTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringTransaction
        fields = [
            'id', 'created_at', 'updated_at',
            'account', 'type', 'description', 'amount', 'category',
            'frequency', 'day_of_month', 'start_date', 'next_date', 'active', 'end_date',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecurringCardPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringCardPurchase
        fields = [
            'id', 'created_at', 'updated_at',
            'card', 'description', 'total_amount', 'installments_total', 'category',
            'frequency', 'day_of_month', 'next_date', 'active', 'end_date',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
