from django.shortcuts import render
from django.views.generic import FormView
from .forms import UserRegistrationForm,UserUpdateForm
from django.contrib.auth import login, logout
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.views import View
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import UserBankAccount


def send_email(user,subject, template):
    message = render_to_string(template, {
        'user' : user,
        })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()
    print("Email sent successfully")
def send_reg_email(user,account_no,subject, template):
    message = render_to_string(template, {
        'user' : user,
        'account_no' : account_no
        })
    send_email = EmailMultiAlternatives(subject, '', to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()
    print("registration Email sent successfully")



class UserRegistrationView(FormView):
    template_name = 'accounts/user_registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('home')
    def form_valid(self,form):
        user = form.save()
        login(self.request, user)
        account_no=user.account.account_no
        send_reg_email(self.request.user,account_no, "Account Registration", "accounts/registration_email.html")
        return super().form_valid(form)
    
class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    def get_success_url(self):
        return reverse_lazy('home')

class UserLogoutView(LogoutView):
    def get_success_url(self):
        if self.request.user.is_authenticated:
            logout(self.request)
        return reverse_lazy('home')


class UserBankAccountUpdateView(View):
    template_name = 'accounts/edit_profile.html'

    def get(self, request):
        form = UserUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('edit_profile')  # Redirect to the user's profile page
        return render(request, self.template_name, {'form': form})
    
def user_logout(request):
    logout(request)
    messages.info(request,"Logged out successfully")
    return redirect('login')

def pass_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user,data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'PassWord Updated Successfully')
            update_session_auth_hash(request,form.user)
            send_email(request.user, "PassWord Change", "accounts/pass_change_email.html")
            return redirect('profile')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'accounts/pass_change.html', {'form': form})

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')