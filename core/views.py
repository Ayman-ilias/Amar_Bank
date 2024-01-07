from django.shortcuts import render
from django.views.generic import TemplateView
# Create your views here.

class HomeView(TemplateView):
    template_name = 'index.html'
class AboutMe(TemplateView):
    template_name = 'about_me.html'

# views.py

from django.shortcuts import render

def about_me(request):
    contact_info = {
        'email': 'aymanilias00@gmail.com',
        'phone': '+8801703645713',
        'linkedin_profile': 'https://www.linkedin.com/in/ayman-ilias-b94082175/',
        # Add other fields as needed
    }

    return render(request, 'about_me.html', {'contact_info': contact_info})
