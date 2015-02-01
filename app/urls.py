from django.conf.urls import url, include
from rest_framework import routers
from rest_framework.authtoken import views
from app.views import UserViewSet, EC2View

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = (
    url(r'api/v1/', include(router.urls)),
    url(r'api/v1/ec2/', EC2View.as_view()),
    url(r'api/v1/auth/', views.obtain_auth_token),
)
