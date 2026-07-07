from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/settings/', views.settings_view, name='settings'),
    path('dashboard/add-server/', views.add_server_view, name='add_server'),
    path('dashboard/start-server/<int:server_id>/', views.start_server_view, name='start_server'),
    path('dashboard/stop-server/<int:server_id>/', views.stop_server_view, name='stop_server'),
    path('dashboard/edit-server/<int:server_id>/', views.edit_server_view, name='edit_server'),
    path('dashboard/playerdata/<int:server_id>/', views.playerdata_view, name='playerdata'),
]
