from django.urls import path
from . import views


# All URLs start witih 'relay/'
urlpatterns = [
    path("<uuid:server_uuid>/", views.relay_lookup, name="relay_lookup"),
]