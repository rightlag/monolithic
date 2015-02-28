import rest_framework.authtoken.views as auth_token
from django.conf.urls import url, include
from rest_framework import routers
from app import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = (
    url(r'api/v1/', include(router.urls)),
    url(r'api/v1/buckets/$', views.BucketList.as_view()),
    url(r'api/v1/buckets/(?P<bucket>(.*))/keys/$',
        views.KeyList.as_view()),
    url(r'api/v1/buckets/(?P<bucket>(.*))/keys/(?P<key>(.*))/$',
        views.KeyDetail.as_view()),
    url(r'api/v1/summary/s3/$', views.S3Summary),
    url(r'api/v1/summary/ec2/$', views.EC2Summary),
    url(r'api/v1/reservations/$', views.ReservationList.as_view()),
    url(r'api/v1/reservations/(?P<reservation_id>(.*))/$',
        views.ReservationDetail.as_view()),
    url(r'api/v1/instances/(?P<instance_id>(.*))/$',
        views.InstanceDetail.as_view()),
    url(r'api/v1/metrics/(?P<instance_id>(.*))/$', views.metrics),
    url(r'api/v1/auth/$', auth_token.obtain_auth_token),
    url(r'api/v1/auth/verify/(?P<verification_code>(.*))/$', views.verify),
)
