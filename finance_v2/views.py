from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

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

from .serializers import (
    AccountSerializer,
    CreditCardSerializer,
    CategorySerializer,
    TagSerializer,
    TransactionSerializer,
    InvoiceSerializer,
    CardChargeSerializer,
    InvoicePaymentSerializer,
    RecurringTransactionSerializer,
    RecurringCardPurchaseSerializer,
)


class UserScopedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        obj = serializer.save()
        return obj


class AccountViewSet(UserScopedModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CreditCardViewSet(UserScopedModelViewSet):
    serializer_class = CreditCardSerializer

    def get_queryset(self):
        return CreditCard.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(UserScopedModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TagViewSet(UserScopedModelViewSet):
    serializer_class = TagSerializer

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(UserScopedModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return (
            Transaction.objects
            .filter(user=self.request.user)
            .select_related("account", "category")
            .prefetch_related("tags")
        )

    def perform_create(self, serializer):
        # Garante que a conta pertence ao usuário
        account = serializer.validated_data.get("account")
        if account and account.user_id != self.request.user.id:
            raise PermissionDenied("Conta inválida para este usuário.")
        serializer.save(user=self.request.user)


class InvoiceViewSet(UserScopedModelViewSet):
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return (
            Invoice.objects
            .select_related("card")
            .filter(card__user=self.request.user)
        )


class CardChargeViewSet(UserScopedModelViewSet):
    serializer_class = CardChargeSerializer

    def get_queryset(self):
        return (
            CardCharge.objects
            .select_related("card", "invoice", "category")
            .filter(card__user=self.request.user)
        )

    def perform_create(self, serializer):
        card = serializer.validated_data.get("card")
        if card and card.user_id != self.request.user.id:
            raise PermissionDenied("Cartão inválido para este usuário.")
        serializer.save()


class InvoicePaymentViewSet(UserScopedModelViewSet):
    serializer_class = InvoicePaymentSerializer

    def get_queryset(self):
        return (
            InvoicePayment.objects
            .select_related("invoice", "account")
            .filter(invoice__card__user=self.request.user)
        )

    def perform_create(self, serializer):
        account = serializer.validated_data.get("account")
        if account and account.user_id != self.request.user.id:
            raise PermissionDenied("Conta inválida para este usuário.")
        invoice = serializer.validated_data.get("invoice")
        if invoice and invoice.card.user_id != self.request.user.id:
            raise PermissionDenied("Fatura inválida para este usuário.")
        serializer.save()


class RecurringTransactionViewSet(UserScopedModelViewSet):
    serializer_class = RecurringTransactionSerializer

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        account = serializer.validated_data.get("account")
        if account and account.user_id != self.request.user.id:
            raise PermissionDenied("Conta inválida para este usuário.")
        serializer.save(user=self.request.user)


class RecurringCardPurchaseViewSet(UserScopedModelViewSet):
    serializer_class = RecurringCardPurchaseSerializer

    def get_queryset(self):
        return RecurringCardPurchase.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        card = serializer.validated_data.get("card")
        if card and card.user_id != self.request.user.id:
            raise PermissionDenied("Cartão inválido para este usuário.")
        serializer.save(user=self.request.user)
