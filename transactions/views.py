from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID,TRANSFER_MONEY,MONEY_RECEIVED
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from datetime import datetime
from django.views import generic
from django.db.models import Sum
from accounts.models import UserBankAccount
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferForm

)
from transactions.models import Transaction
from smtplib import SMTPException
from email.mime.text import MIMEText

# def send_email(to_email, subject, message):
#     try:
#         smtp_server = "smtp.gmail.com" # replace with your SMTP server
#         port = 587 # for starttls
#         sender_email = "aymanilias02@gmail.com" # replace with your email
#         password = "ggvp pvnj vbql ifze" # replace with your password

#         # set up the smtp server
#         server = smtplib.SMTP(smtp_server, port)
#         server.ehlo() # can be omitted
#         server.starttls() # secure the connection
#         server.login(sender_email, password)

#         # create the message
#         msg = MIMEText(message)
#         msg['Subject'] = subject
#         msg['From'] = sender_email
#         msg['To'] = to_email

#         # send the message
#         server.sendmail(sender_email, [to_email], msg.as_string())

#         # close the server
#         server.close()

#         print("Successfully sent email to %s:" % (to_email))
#     except Exception as e:
#         print("Failed to send email to %s:" % (to_email))
#         print(e)


def send_transaction_email(user, amount, subject, template):
    message = render_to_string(template, {
        'user' : user,
        'amount' : amount,
        })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()
    print("Email sent successfully")  # Optional: Include a success message for debugging



class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        send_transaction_email(self.request.user, amount, "Deposite Message", "transactions/deposite_email.html")
        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')

        self.request.user.account.balance -= form.cleaned_data.get('amount')
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        send_transaction_email(self.request.user, amount, "Withdrawal Message", "transactions/withdrawal_email.html")
        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )
        send_transaction_email(self.request.user, amount, "Loan Request Message", "transactions/loan_email.html")
        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
                # Reduce the loan amount from the user's balance
                # 5000, 500 + 5000 = 5500
                # balance = 3000, loan = 5000
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        # print(queryset)
        return queryset
    


# class MoneyTransferView(TransactionCreateMixin):
#     form_class = MoneyTransferForm
#     title = 'Transfer Money'

#     def get_initial(self):
#         initial = {'transaction_type': TRANSFER_MONEY}
#         return initial

#     def form_valid(self, form):
#         amount = form.cleaned_data.get('amount')
#         sender_account = self.request.user.account
#         receiver_account = form.cleaned_data.get('account')

#         if amount > sender_account.balance:
#             messages.error(
#                 self.request,
#                 f'You do not have sufficient balance to transfer {amount}$'
#             )
#             return super().form_invalid(form)

#         sender= Transaction.objects.create(
#             account=sender_account,
#             amount=-amount,
#             balance_after_transaction=sender_account.balance - amount,
#             transaction_type=TRANSFER_MONEY,
#         )

#         receiver= Transaction.objects.create(
#             account=receiver_account,
#             amount=amount,
#             balance_after_transaction=receiver_account.balance + amount,
#             transaction_type=MONEY_RECEIVED,
#         )

#         sender_account.balance -= amount
#         receiver_account.balance += amount

#         sender_account.save(update_fields=['balance'])
#         receiver_account.save(update_fields=['balance'])

#         messages.success(
#             self.request,
#             f'Successfully transferred {"{:,.2f}".format(float(amount))}$ to {receiver_account.user.username}'
#         )
#         send_transaction_email(self.request.user, amount, "Transfer Money Message", "transactions/transfer_email.html")

#         return super().form_valid(form)


# class MoneyTransferView(TransactionCreateMixin):
#     form_class = MoneyTransferForm
#     title = 'Transfer Money'

#     def get_initial(self):
#         initial = {'transaction_type': TRANSFER_MONEY}
#         return initial

#     def form_valid(self, form):
#         amount = form.cleaned_data.get('amount')
#         sender_account = self.request.user.account
#         receiver_account = form.cleaned_data.get('account')

#         if amount > sender_account.balance:
#             messages.error(
#                 self.request,
#                 f'You do not have sufficient balance to transfer {amount}$'
#             )
#             return super().form_invalid(form)
        
#         sender_transaction = Transaction.objects.create(
#             account=sender_account,
#             amount=-amount,
#             balance_after_transaction=sender_account.balance - amount,
#             transaction_type=TRANSFER_MONEY,
#         )

#         receiver_transaction = Transaction.objects.create(
#             account=receiver_account,
#             amount=amount,
#             balance_after_transaction=receiver_account.balance + amount,
#             transaction_type=MONEY_RECEIVED,
#         )

#         sender_account.balance -= amount
#         receiver_account.balance += amount

#         sender_account.save(update_fields=['balance'])
#         receiver_account.save(update_fields=['balance'])

#         messages.success(
#             self.request,
#             f'Successfully transferred {"{:,.2f}".format(float(amount))}$ to {receiver_account.user.username}'
#         )

#         send_transaction_email(self.request.user, amount, "Transfer Money Message", "transactions/transfer_email.html")

#         send_transaction_email(receiver_account.user, amount, "Money Received Message", "transactions/money_received_email.html")

#         return super().form_valid(form)



# class MoneyTransferView(LoginRequiredMixin, generic.FormView):
#     form_class = MoneyTransferForm
#     template_name = 'transactions/transfer.html'

#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['user_accounts'] = self.request.user.account.all()
#         kwargs['recipient_accounts'] = Transaction.objects.filter(user=self.request.user)
#         return kwargs
    
#     def form_valid(self, form):
#         sender_account = form.cleaned_data['account']
#         recipient_account = form.cleaned_data['recipient_account']
#         amount = form.cleaned_data['amount']

#         sender_account.balance -= amount
#         recipient_account.balance += amount

#         sender_account.save()
#         recipient_account.save()

#         Transaction.objects.create(account=sender_account, amount=-amount, transaction_type=Transaction.WITHDRAWAL)
#         Transaction.objects.create(account=recipient_account, amount=amount, transaction_type=Transaction.DEPOSIT)

#         return super().form_valid(form)
    
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.views.generic.edit import CreateView
# from .models import Transaction
# from .forms import TransferForm

# class TransferView(LoginRequiredMixin, CreateView):
#     template_name = 'transactions/transfer.html'
#     form_class = TransferForm
#     success_url = reverse_lazy('transaction_report')

#     def form_valid(self, form):
#         sender_account = self.request.user.account
#         recipient_account = form.cleaned_data.get('account')
#         amount = form.cleaned_data.get('amount')

#         if amount > sender_account.balance:
#             messages.error(
#                 self.request,
#                 f'Insufficient balance to transfer {"{:,.2f}".format(float(amount))}$'
#             )

            
            
#             return redirect('transaction_report')

#         transaction = Transaction.objects.create(
#             account=sender_account,
#             transaction_type=5,
#             amount=-amount,
#             related_account=recipient_account,
            
#         )

#         transaction = Transaction.objects.create(
#             account=recipient_account,
#             transaction_type=6,
#             amount=amount,
#             related_account=sender_account,
#         )

#         messages.success(
#             self.request,
#             f'Money transfer of {"{:,.2f}".format(float(amount))}$ successful'
#         )

#         return super().form_valid(form)
    
class TransferView(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transfer.html'
    form_class = TransferForm
    success_url = reverse_lazy('transaction_report')
    title = 'Transfer Money'

    def form_valid(self, form):
        sender_account = self.request.user.account
        recipient_account = form.cleaned_data.get('account')
        amount = form.cleaned_data.get('amount')
        # recipient_account = UserBankAccount.objects.get(id=account)
        

        if amount > sender_account.balance:
            messages.error(
                self.request,
                f'Insufficient balance to transfer {"{:,.2f}".format(float(amount))}$'
            )
            return redirect('transfer')
        elif recipient_account == sender_account:
            messages.error(
                self.request,
                f'You Can not transfer money to your account'
            )
            return redirect('transfer')
        else:    
            sender_transaction = Transaction.objects.create(
                account=sender_account,
                transaction_type=TRANSFER_MONEY, 
                amount=amount,
                balance_after_transaction=sender_account.balance - amount,
                # related_account=recipient_account,
            )
            receiver_transaction = Transaction.objects.create(
                account=recipient_account,
                transaction_type=MONEY_RECEIVED,
                amount=amount,
                balance_after_transaction=recipient_account.balance + amount,
                # related_account=sender_account,
            )

            sender_account.balance -= amount
            recipient_account.balance += amount

            sender_account.save(update_fields=['balance'])
            recipient_account.save(update_fields=['balance'])


            messages.success(
                self.request,
                f'Money transfer of {"{:,.2f}".format(float(amount))}$ successful to {recipient_account} '
            )
            send_transaction_email(self.request.user, amount, "Transfer Money Message", "transactions/transfer_email.html")

            send_transaction_email(recipient_account.user, amount, "Money Received Message", "transactions/money_received_email.html")

        return super().form_valid(form)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'titlenew': self.title
        })

        return context

