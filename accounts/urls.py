
from django.urls import path
from .views import UserRegistrationView, UserLoginView, UserLogoutView,UserBankAccountUpdateView
from .import views
 
urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    # path('logout/', UserLogoutView.as_view(), name='logout'),
    path('logout/', views.user_logout, name='logout'),
    path('edit_profile/', UserBankAccountUpdateView.as_view(), name='edit_profile' ),
     path('pass_change',views.pass_change, name='pass_change'),
    path('profile/',views.profile, name='profile'),
]