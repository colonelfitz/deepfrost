from django.conf.urls import url
from frizzy import views

urlpatterns = [
    url(r'^server_time$', views.get_server_time, name='get_server_time'),
    url(r'^server_host$', views.get_host_name, name='get_host_name'),
    url(r'^send/easy_trader$', views.send_easy_trader, name='send_easy_trader'),
    url(r'^send/online_plus$', views.send_online_plus, name='send_online_plus'),
    url(r'^send/agah_online$', views.send_agah_online, name='send_agah_online'),
    url(r'^send/farabixo$', views.send_farabixo, name='send_farabixo'),
]

