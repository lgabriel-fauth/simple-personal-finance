from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("accounts/", views.AccountListView.as_view(), name="account_list"),
    path("accounts/new/", views.AccountCreateView.as_view(), name="account_create"),
    path("accounts/<int:pk>/edit/", views.AccountUpdateView.as_view(), name="account_update"),
    path("accounts/<int:pk>/delete/", views.AccountDeleteView.as_view(), name="account_delete"),

    path("cards/", views.CreditCardListView.as_view(), name="card_list"),
    path("cards/new/", views.CreditCardCreateView.as_view(), name="card_create"),
    path("cards/<int:pk>/edit/", views.CreditCardUpdateView.as_view(), name="card_update"),
    path("cards/<int:pk>/delete/", views.CreditCardDeleteView.as_view(), name="card_delete"),

    path("transactions/", views.TransactionListView.as_view(), name="transaction_list"),
    path("transactions/new/", views.TransactionCreateView.as_view(), name="transaction_create"),
    path("transactions/<int:pk>/edit/", views.TransactionUpdateView.as_view(), name="transaction_update"),
    path("transactions/<int:pk>/delete/", views.TransactionDeleteView.as_view(), name="transaction_delete"),
    path("transfers/new/", views.TransferCreateView.as_view(), name="transfer_create"),
    path("transactions/<int:pk>/toggle/", views.ToggleReconciliationView.as_view(), name="transaction_toggle"),

    path("purchases/new/", views.PurchaseCreateView.as_view(), name="purchase_create"),
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/pay/", views.InvoicePaymentCreateView.as_view(), name="invoice_payment"),
    path("invoices/<int:pk>/close/", views.InvoiceCloseView.as_view(), name="invoice_close"),
    path("invoices/<int:pk>/open/", views.InvoiceOpenView.as_view(), name="invoice_open"),
    path("payments/<int:pk>/edit/", views.InvoicePaymentUpdateView.as_view(), name="invoice_payment_update"),
    path("payments/<int:pk>/delete/", views.InvoicePaymentDeleteView.as_view(), name="invoice_payment_delete"),

    # Compras no cartão - editar lançamento
    path("charges/<int:pk>/edit/", views.CardChargeUpdateView.as_view(), name="cardcharge_update"),
    path("charges/<int:pk>/delete/", views.CardChargeDeleteView.as_view(), name="cardcharge_delete"),

    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/new/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    path("tags/", views.TagListView.as_view(), name="tag_list"),
    path("tags/new/", views.TagCreateView.as_view(), name="tag_create"),
    path("tags/<int:pk>/edit/", views.TagUpdateView.as_view(), name="tag_update"),
    path("tags/<int:pk>/delete/", views.TagDeleteView.as_view(), name="tag_delete"),

    path("statement/", views.StatementView.as_view(), name="statement"),

    # Recorrentes - transações em conta
    path("recurrents/transactions/", views.RecurringTransactionListView.as_view(), name="rec_tx_list"),
    path("recurrents/transactions/new/", views.RecurringTransactionCreateView.as_view(), name="rec_tx_create"),
    path("recurrents/transactions/<int:pk>/edit/", views.RecurringTransactionUpdateView.as_view(), name="rec_tx_update"),
    path("recurrents/transactions/<int:pk>/delete/", views.RecurringTransactionDeleteView.as_view(), name="rec_tx_delete"),
    path("recurrents/transactions/<int:pk>/generate/", views.RecurringTransactionGenerateView.as_view(), name="rec_tx_generate"),

    # Recorrentes - compras no cartão
    path("recurrents/cards/", views.RecurringCardPurchaseListView.as_view(), name="rec_card_list"),
    path("recurrents/cards/new/", views.RecurringCardPurchaseCreateView.as_view(), name="rec_card_create"),
    path("recurrents/cards/<int:pk>/edit/", views.RecurringCardPurchaseUpdateView.as_view(), name="rec_card_update"),
    path("recurrents/cards/<int:pk>/delete/", views.RecurringCardPurchaseDeleteView.as_view(), name="rec_card_delete"),
    path("recurrents/cards/<int:pk>/generate/", views.RecurringCardPurchaseGenerateView.as_view(), name="rec_card_generate"),
]
