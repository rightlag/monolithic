import boto.ec2

from app import core
from rest_framework.response import Response
from rest_framework import status
from functools import wraps

def validate_region(fn):
    """Validate `region` argument to ensure AWS Region is valid."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        conn = boto.ec2.connect_to_region(core.DEFAULT_AWS_REGION)
        region = kwargs.get('region')
        if region not in [region.name for region in conn.get_all_regions()]:
            return Response('Invalid AWS Region specified',
                            status=status.HTTP_400_BAD_REQUEST)
        return fn(*args, **kwargs)
    return wrapper
