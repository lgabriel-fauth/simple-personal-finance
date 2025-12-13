from django.urls import path, include
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'accounts', views.AccountViewSet, basename='finance-v2-accounts')
router.register(r'credit-cards', views.CreditCardViewSet, basename='finance-v2-credit-cards')
router.register(r'categories', views.CategoryViewSet, basename='finance-v2-categories')
router.register(r'tags', views.TagViewSet, basename='finance-v2-tags')
router.register(r'transactions', views.TransactionViewSet, basename='finance-v2-transactions')
router.register(r'invoices', views.InvoiceViewSet, basename='finance-v2-invoices')
router.register(r'card-charges', views.CardChargeViewSet, basename='finance-v2-card-charges')
router.register(r'invoice-payments', views.InvoicePaymentViewSet, basename='finance-v2-invoice-payments')
router.register(r'recurring-transactions', views.RecurringTransactionViewSet, basename='finance-v2-recurring-transactions')
router.register(r'recurring-card-purchases', views.RecurringCardPurchaseViewSet, basename='finance-v2-recurring-card-purchases')

urlpatterns = [
    path('', include(router.urls)),
]
