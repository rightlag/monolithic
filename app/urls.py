import rest_framework.authtoken.views as auth_token
from django.conf.urls import url, include
from rest_framework import routers
from app import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'keypairs', views.KeypairViewSet)
router.register(r'policies', views.PolicyViewSet)

# Separate to another module (e.g. `core.py`)
BASE_URL_REGION = r'api/v1/(?P<region>\w+(-\w+)+)'

urlpatterns = (
    url(r'api/v1/', include(router.urls)),
    url(BASE_URL_REGION + '/buckets/$', views.BucketList.as_view()),
    url(BASE_URL_REGION + r'/buckets/(?P<bucket>(.*))/$',
        views.BucketDetail.as_view()),
    url(BASE_URL_REGION + '/billing/$', views.BillingList.as_view()),
    url(BASE_URL_REGION + '/billing/plots/$',
        views.BillingDataPlots.as_view()),
    url(BASE_URL_REGION + '/summary/s3/$', views.S3Summary),
    url(BASE_URL_REGION + '/summary/ec2/$', views.EC2Summary),
    url(BASE_URL_REGION + '/reservations/$', views.ReservationList.as_view()),
    url(BASE_URL_REGION + r'/reservations/(?P<reservation_id>(.*))/$',
        views.ReservationDetail.as_view()),
    url(BASE_URL_REGION + r'/instances/(?P<instance_id>(.*))/$',
        views.InstanceDetail.as_view()),
    url(BASE_URL_REGION + r'/pricing/(?P<instance_id>(.*))/$',
        views.spot_price_history),
    url(BASE_URL_REGION + r'/metrics/(?P<instance_id>(.*))/$', views.metrics),
    url(r'api/v1/auth/$', auth_token.obtain_auth_token),
    url(r'api/v1/auth/verify/(?P<verification_code>(.*))/$', views.verify),
    url(r'api/v1/auth/access/$', views.access),
)
