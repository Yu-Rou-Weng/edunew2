from django.urls import path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from .views import (
    AuthCallbackView,
    AuthView,
    ExecutionView,
    IndexView,
    LoginView,
    LogoutView,
    SetupView,
)

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('auth/', AuthView.as_view(), name='auth'),
    path('auth/callback/', AuthCallbackView.as_view(), name='authcallback'),
    path('login/<int:u_id>/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('setup/<int:u_id>/<int:p_id>/<int:do_id>/',
         SetupView.as_view(),
         name='setup'),
    path('execution/<int:u_id>/<int:p_id>/',
         ExecutionView.as_view(),
         name='execution'),
] + staticfiles_urlpatterns()
