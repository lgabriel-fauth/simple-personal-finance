from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.views import View
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.contrib import messages
from .models import Account, CreditCard
from .models import Transaction
from django.db import transaction as db_transaction
from .forms import TransactionForm, TransferForm
from .forms import PurchaseForm, InvoicePaymentForm, StatementFilterForm
from .forms import RecurringTransactionForm, RecurringCardPurchaseForm
from .forms import CardChargeForm
from .models import Invoice, CardCharge, InvoicePayment, Category, Tag, RecurringTransaction, RecurringCardPurchase
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum
import calendar

# Create your views here.


class UserQuerysetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)


class UserCreateMixin:
    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()
        return super().form_valid(form)


class CardChargeDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = CardCharge
    template_name = "finance/confirm_delete.html"

    def get_queryset(self):
        obj = CardCharge.objects.filter(card__user=self.request.user).select_related("invoice")
        return obj

    def post(self, request, *args, **kwargs):
        print('teste')
        obj = self.get_object()
        old_invoice = obj.invoice
        obj.delete()
        # Se a fatura ficou vazia, exclui; senão redireciona para o detalhe dela
        try:
            if old_invoice and not old_invoice.charges.exists() and not old_invoice.payments.exists():
                old_invoice.delete()
                next_url = reverse_lazy("finance:invoice_list")
            else:
                next_url = reverse_lazy("finance:invoice_detail", kwargs={"pk": old_invoice.pk})
        except Exception:
            next_url = reverse_lazy("finance:invoice_list")
        messages.success(self.request, "Compra excluída com sucesso.")
        return HttpResponseRedirect(next_url)

class CardChargeUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = CardCharge
    form_class = CardChargeForm
    template_name = "finance/cardcharge_form.html"

    def get_queryset(self):
        return CardCharge.objects.filter(card__user=self.request.user).select_related("card", "invoice")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        obj = self.object
        return reverse_lazy("finance:invoice_detail", kwargs={"pk": obj.invoice_id})

    def form_valid(self, form):
        old_obj = self.get_object()
        old_invoice = old_obj.invoice
        obj = form.save(commit=False)
        # Reatribui a fatura com base em card+date
        inv = Invoice.assign_invoice_for(obj.card, obj.date)
        if inv.status == Invoice.Status.CLOSED:
            inv = inv.next_invoice()
        obj.invoice = inv
        obj.save()
        form.save_m2m()
        messages.success(self.request, "Lançamento atualizado com sucesso.")
        # Se a fatura anterior ficou vazia (sem compras e sem pagamentos), exclui
        try:
            if old_invoice and old_invoice.pk != inv.pk:
                has_charges = old_invoice.charges.exists()
                has_payments = old_invoice.payments.exists()
                if not has_charges and not has_payments:
                    old_invoice.delete()
        except Exception:
            pass
        return super().form_valid(form)


class InvoiceCloseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        inv = Invoice.objects.filter(pk=pk, card__user=request.user).select_related("card").first()
        if not inv:
            return HttpResponseForbidden()
        if inv.status == Invoice.Status.OPEN or inv.status == Invoice.Status.PARTIAL:
            inv.status = Invoice.Status.CLOSED
            if not inv.closing_date:
                try:
                    inv.closing_date = date(inv.year, inv.month, min(inv.card.closing_day, 28))
                except Exception:
                    pass
            if not inv.due_date:
                vy, vm = (inv.year + 1, 1) if inv.month == 12 else (inv.year, inv.month + 1)
                try:
                    inv.due_date = date(vy, vm, min(inv.card.due_day, 28))
                except Exception:
                    pass
            inv.save()
            # Garantir existência da próxima fatura (projeção)
            inv.next_invoice()
            messages.success(request, "Fatura fechada e próxima fatura projetada.")
        return HttpResponseRedirect(reverse_lazy("finance:invoice_detail", kwargs={"pk": pk}))


class StatementView(LoginRequiredMixin, generic.TemplateView):
    template_name = "finance/statement.html"

    def get(self, request, *args, **kwargs):
        self.form = StatementFilterForm(request.GET or None, user=request.user)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = getattr(self, 'form', None) or StatementFilterForm(user=self.request.user)
        qs = Transaction.objects.filter(user=self.request.user).select_related("account", "category").prefetch_related("tags")
        if form.is_valid():
            account = form.cleaned_data.get("account")
            start_date = form.cleaned_data.get("start_date")
            end_date = form.cleaned_data.get("end_date")
            typ = form.cleaned_data.get("type")
            category = form.cleaned_data.get("category")
            tag = form.cleaned_data.get("tag")
            reconciled = form.cleaned_data.get("reconciled")
            if account:
                qs = qs.filter(account=account)
            if start_date:
                qs = qs.filter(date__gte=start_date)
            if end_date:
                qs = qs.filter(date__lte=end_date)
            if typ:
                qs = qs.filter(type=typ)
            if category:
                qs = qs.filter(category=category)
            if tag:
                qs = qs.filter(tags=tag)
            if reconciled == '1':
                qs = qs.filter(reconciled=True)
            elif reconciled == '0':
                qs = qs.filter(reconciled=False)
        ctx['form'] = form
        ctx['object_list'] = qs.order_by('-date', '-id')
        return ctx


class ToggleReconciliationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        tx = Transaction.objects.filter(pk=pk, user=request.user).first()
        if not tx:
            return HttpResponseForbidden()
        tx.reconciled = not tx.reconciled
        tx.save(update_fields=["reconciled"])
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse_lazy("finance:statement")
        return HttpResponseRedirect(next_url)


# Recurring - Transactions
class RecurringTransactionListView(LoginRequiredMixin, generic.ListView):
    model = RecurringTransaction
    template_name = "finance/rec_tx_list.html"

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user).select_related("account", "category")


class RecurringTransactionCreateView(LoginRequiredMixin, generic.CreateView):
    model = RecurringTransaction
    form_class = RecurringTransactionForm
    template_name = "finance/rec_tx_form.html"
    success_url = reverse_lazy("finance:rec_tx_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()
        messages.success(self.request, "Recorrência criada com sucesso.")
        return super().form_valid(form)


class RecurringTransactionUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = RecurringTransaction
    form_class = RecurringTransactionForm
    template_name = "finance/rec_tx_form.html"
    success_url = reverse_lazy("finance:rec_tx_list")

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RecurringTransactionDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = RecurringTransaction
    template_name = "finance/confirm_delete.html"
    success_url = reverse_lazy("finance:rec_tx_list")

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Recorrência excluída com sucesso.")
        return super().delete(request, *args, **kwargs)


class RecurringTransactionGenerateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        obj = RecurringTransaction.objects.filter(pk=pk, user=request.user).first()
        if not obj:
            return HttpResponseForbidden()
        with db_transaction.atomic():
            obj.generate_next()
        next_url = request.POST.get("next") or reverse_lazy("finance:rec_tx_list")
        messages.success(request, "Ocorrência gerada com sucesso.")
        return HttpResponseRedirect(next_url)


# Recurring - Card Purchases
class RecurringCardPurchaseListView(LoginRequiredMixin, generic.ListView):
    model = RecurringCardPurchase
    template_name = "finance/rec_card_list.html"

    def get_queryset(self):
        return RecurringCardPurchase.objects.filter(user=self.request.user).select_related("card", "category")


class RecurringCardPurchaseCreateView(LoginRequiredMixin, generic.CreateView):
    model = RecurringCardPurchase
    form_class = RecurringCardPurchaseForm
    template_name = "finance/rec_card_form.html"
    success_url = reverse_lazy("finance:rec_card_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()
        return super().form_valid(form)


class RecurringCardPurchaseUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = RecurringCardPurchase
    form_class = RecurringCardPurchaseForm
    template_name = "finance/rec_card_form.html"
    success_url = reverse_lazy("finance:rec_card_list")

    def get_queryset(self):
        return RecurringCardPurchase.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class RecurringCardPurchaseDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = RecurringCardPurchase
    template_name = "finance/confirm_delete.html"
    success_url = reverse_lazy("finance:rec_card_list")

    def get_queryset(self):
        return RecurringCardPurchase.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Recorrência de cartão excluída com sucesso.")
        return super().delete(request, *args, **kwargs)


class RecurringCardPurchaseGenerateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        obj = RecurringCardPurchase.objects.filter(pk=pk, user=request.user).first()
        if not obj:
            return HttpResponseForbidden()
        with db_transaction.atomic():
            obj.generate_next()
        next_url = request.POST.get("next") or reverse_lazy("finance:rec_card_list")
        messages.success(request, "Ocorrência gerada com sucesso.")
        return HttpResponseRedirect(next_url)


# Category CRUD
class CategoryListView(LoginRequiredMixin, generic.ListView):
    model = Category
    template_name = "finance/category_list.html"

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).select_related("parent")


class CategoryCreateView(LoginRequiredMixin, generic.CreateView):
    model = Category
    fields = ["name", "kind", "parent"]
    template_name = "finance/category_form.html"
    success_url = reverse_lazy("finance:category_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["parent"].queryset = Category.objects.filter(user=self.request.user)
        return form

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Category
    fields = ["name", "kind", "parent"]
    template_name = "finance/category_form.html"
    success_url = reverse_lazy("finance:category_list")

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["parent"].queryset = Category.objects.filter(user=self.request.user).exclude(pk=self.object.pk)
        return form

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Categoria atualizada com sucesso.")
        return resp


class CategoryDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Category
    template_name = "finance/confirm_delete.html"
    success_url = reverse_lazy("finance:category_list")

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Categoria excluída com sucesso.")
        return super().delete(request, *args, **kwargs)


# Tag CRUD
class TagListView(LoginRequiredMixin, generic.ListView):
    model = Tag
    template_name = "finance/tag_list.html"

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


class DashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = "finance/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Saldos por conta: saldo = initial_balance + entradas - saídas
        accounts = Account.objects.filter(user=user, active=True).order_by("name")
        account_balances = []
        for acc in accounts:
            tx = Transaction.objects.filter(user=user, account=acc)
            ins = tx.filter(type=Transaction.TxType.INCOME).aggregate(s=Sum("amount")).get("s") or Decimal("0")
            outs = tx.filter(type=Transaction.TxType.OUTCOME).aggregate(s=Sum("amount")).get("s") or Decimal("0")
            balance = Decimal(acc.initial_balance) + ins - outs
            account_balances.append({
                "account": acc,
                "balance": balance,
            })

        # Despesas por categoria no mês atual (contas)
        today = date.today()
        month_start = date(today.year, today.month, 1)
        # último dia do mês
        next_month = date(today.year + (today.month // 12), 1 if today.month == 12 else today.month + 1, 1)
        month_end = next_month - timedelta(days=1)
        qs_out = Transaction.objects.filter(
            user=user,
            type=Transaction.TxType.OUTCOME,
            date__gte=month_start,
            date__lte=month_end,
        ).select_related("category")
        expenses_by_category = {}
        for t in qs_out:
            key = t.category.name if t.category else "Sem categoria"
            expenses_by_category[key] = expenses_by_category.get(key, Decimal("0")) + t.amount

        # Compras no cartão no mês corrente (por fatura de competencia = ano/mes)
        card_purchases = CardCharge.objects.filter(
            card__user=user,
            date__gte=month_start,
            date__lte=month_end,
        ).select_related("card", "invoice", "category")

        # Alertas de vencimento de faturas (próximos 7 dias)
        upcoming = Invoice.objects.filter(
            card__user=user,
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7),
        ).exclude(status=Invoice.Status.PAID).select_related("card").order_by("due_date")

        ctx.update({
            "account_balances": account_balances,
            "expenses_by_category": expenses_by_category,
            "card_purchases": card_purchases,
            "upcoming_invoices": upcoming,
            "month_start": month_start,
            "month_end": month_end,
        })
        return ctx


class TagCreateView(LoginRequiredMixin, generic.CreateView):
    model = Tag
    fields = ["name"]
    template_name = "finance/tag_form.html"
    success_url = reverse_lazy("finance:tag_list")

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()
        return super().form_valid(form)


class TagUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Tag
    fields = ["name"]
    template_name = "finance/tag_form.html"
    success_url = reverse_lazy("finance:tag_list")

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)


class TagDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Tag
    template_name = "finance/confirm_delete.html"
    success_url = reverse_lazy("finance:tag_list")

    def get_queryset(self):
        return Tag.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Tag excluída com sucesso.")
        return super().delete(request, *args, **kwargs)


class AccountListView(LoginRequiredMixin, UserQuerysetMixin, generic.ListView):
    model = Account
    template_name = "finance/account_list.html"


class AccountCreateView(LoginRequiredMixin, UserCreateMixin, generic.CreateView):
    model = Account
    fields = ["name", "type", "initial_balance", "currency", "active"]
    success_url = reverse_lazy("finance:account_list")
    template_name = "finance/account_form.html"
    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Conta criada com sucesso.")
        return resp


class AccountUpdateView(LoginRequiredMixin, UserQuerysetMixin, generic.UpdateView):
    model = Account
    fields = ["name", "type", "initial_balance", "currency", "active"]
    success_url = reverse_lazy("finance:account_list")
    template_name = "finance/account_form.html"


class AccountDeleteView(LoginRequiredMixin, UserQuerysetMixin, generic.DeleteView):
    model = Account
    success_url = reverse_lazy("finance:account_list")
    template_name = "finance/confirm_delete.html"
    
    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Conta excluída com sucesso.")
        return super().delete(request, *args, **kwargs)


class CreditCardListView(LoginRequiredMixin, UserQuerysetMixin, generic.ListView):
    model = CreditCard
    template_name = "finance/creditcard_list.html"


class CreditCardCreateView(LoginRequiredMixin, UserCreateMixin, generic.CreateView):
    model = CreditCard
    fields = ["name", "brand", "limit", "closing_day", "due_day", "active"]
    success_url = reverse_lazy("finance:card_list")
    template_name = "finance/creditcard_form.html"
    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Cartão criado com sucesso.")
        return resp


class CreditCardUpdateView(LoginRequiredMixin, UserQuerysetMixin, generic.UpdateView):
    model = CreditCard
    fields = ["name", "brand", "limit", "closing_day", "due_day", "active"]
    success_url = reverse_lazy("finance:card_list")
    template_name = "finance/creditcard_form.html"


class CreditCardDeleteView(LoginRequiredMixin, UserQuerysetMixin, generic.DeleteView):
    model = CreditCard
    success_url = reverse_lazy("finance:card_list")
    template_name = "finance/confirm_delete.html"

    def post(self, request, *args, **kwargs):
        messages.success(self.request, "Cartão de crédito excluído com sucesso.")
        return super().delete(request, *args, **kwargs)


class TransactionListView(LoginRequiredMixin, generic.ListView):
    model = Transaction
    template_name = "finance/transaction_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user).select_related("account", "category").prefetch_related("tags")


class TransactionCreateView(LoginRequiredMixin, generic.CreateView):
    model = Transaction
    form_class = TransactionForm
    success_url = reverse_lazy("finance:transaction_list")
    template_name = "finance/transaction_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        obj.save()
        form.save_m2m()
        messages.success(self.request, "Lançamento criado com sucesso.")
        return super().form_valid(form)


class TransferCreateView(LoginRequiredMixin, generic.FormView):
    form_class = TransferForm
    template_name = "finance/transfer_form.html"
    success_url = reverse_lazy("finance:transaction_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        from_acc = form.cleaned_data["from_account"]
        to_acc = form.cleaned_data["to_account"]
        date = form.cleaned_data["date"]
        description = form.cleaned_data["description"]
        amount = form.cleaned_data["amount"]

        import uuid
        tkey = str(uuid.uuid4())

        with db_transaction.atomic():
            Transaction.objects.create(
                user=self.request.user,
                account=from_acc,
                type=Transaction.TxType.OUTCOME,
                date=date,
                description=description,
                amount=amount,
                transfer_key=tkey,
            )
            Transaction.objects.create(
                user=self.request.user,
                account=to_acc,
                type=Transaction.TxType.INCOME,
                date=date,
                description=description,
                amount=amount,
                transfer_key=tkey,
            )
        messages.success(self.request, "Transferência registrada com sucesso.")
        return super().form_valid(form)


def add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    day = min(d.day, last_day)
    return date(y, m, day)


class PurchaseCreateView(LoginRequiredMixin, generic.FormView):
    form_class = PurchaseForm
    template_name = "finance/purchase_form.html"
    success_url = reverse_lazy("finance:invoice_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        card = form.cleaned_data["card"]
        pdate = form.cleaned_data["date"]
        description = form.cleaned_data["description"]
        total = form.cleaned_data["total_amount"]
        parcels = form.cleaned_data["installments_total"]
        category = form.cleaned_data.get("category")

        per_parcel = (total / parcels).quantize(Decimal("0.01")) if parcels > 1 else total

        with db_transaction.atomic():
            for i in range(1, parcels + 1):
                charge_date = add_months(pdate, i - 1)
                inv = Invoice.assign_invoice_for(card, charge_date)
                if inv.status == Invoice.Status.CLOSED:
                    inv = inv.next_invoice()
                CardCharge.objects.create(
                    card=card,
                    invoice=inv,
                    date=charge_date,
                    description=description,
                    total_amount=per_parcel,
                    installment_number=i,
                    installments_total=parcels,
                    category=category,
                )
        messages.success(self.request, "Compra registrada com sucesso.")
        return super().form_valid(form)


class InvoiceListView(LoginRequiredMixin, generic.ListView):
    model = Invoice
    template_name = "finance/invoice_list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(card__user=self.request.user).select_related("card").order_by('year', 'month')


class InvoiceDetailView(LoginRequiredMixin, generic.DetailView):
    model = Invoice
    template_name = "finance/invoice_detail.html"

    def get_queryset(self):
        return super().get_queryset().filter(card__user=self.request.user).select_related("card").prefetch_related("charges", "payments")


class InvoicePaymentCreateView(LoginRequiredMixin, generic.FormView):
    form_class = InvoicePaymentForm
    template_name = "finance/invoice_payment_form.html"

    def get_success_url(self):
        return reverse_lazy("finance:invoice_detail", kwargs={"pk": self.kwargs["pk"]})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        inv = Invoice.objects.filter(pk=self.kwargs["pk"], card__user=self.request.user).select_related("card").first()
        if not inv:
            form.add_error(None, "Fatura não encontrada")
            return self.form_invalid(form)

        account = form.cleaned_data["account"]
        pdate = form.cleaned_data["date"]
        amount = form.cleaned_data["amount"]
        kind = form.cleaned_data["kind"]

        with db_transaction.atomic():
            InvoicePayment.objects.create(invoice=inv, account=account, date=pdate, amount=amount, kind=kind)
            Transaction.objects.create(
                user=self.request.user,
                account=account,
                type=Transaction.TxType.OUTCOME,
                date=pdate,
                description=f"Pagamento fatura {inv.card.name} {inv.month:02d}/{inv.year}",
                amount=amount,
            )
            # Atualiza status da fatura
            bal = inv.balance()
            if bal <= 0:
                inv.status = Invoice.Status.PAID
            elif amount > 0:
                inv.status = Invoice.Status.PARTIAL
            inv.save()
        messages.success(self.request, "Pagamento registrado com sucesso.")
        return super().form_valid(form)
