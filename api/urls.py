from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken import views as auth_views

from . import views


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    path('', views.home, name='home'),
    path('', include(router.urls)),
    
    # Rotas de autenticação
    path('auth/login/', views.login_by_email, name='api_email_auth'),
    path('auth/logout/', views.logout_view, name='api_logout'),
    path('auth/user/', views.current_user, name='api_current_user'),
]