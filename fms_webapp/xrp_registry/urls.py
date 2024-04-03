
from django.urls import include, re_path

from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'devices', views.DeviceViewSet)

urlpatterns = [
    re_path(r'^api/', include(router.urls)),

    re_path(r'^home/', views.home, name='home'),
    re_path(r'^register/', views.register, name='register'),
    re_path(r'^status/', views.status, name='status'),

]
