import boto.exception
import boto.s3
import itertools
import pandas
import re

from datetime import datetime

__author__ = 'Jason Walsh'

DEFAULT_AWS_REGION = 'us-east-1'

class Billing(object):
    def __init__(self, region=DEFAULT_AWS_REGION, bucket=''):
        conn = boto.s3.connect_to_region(region)
        self.bucket = conn.get_bucket(bucket)

    def _parse_contents(self, contents):
        """Parse the contents of the AWS billing CSV file and return
        both the headers and the contents of the file."""
        pattern = r'(,)(?=(?:[^"]|"[^"]*")*$)'
        # Convert string object from CSV to DSV format. This prevents
        # certain columns (e.g. `TaxationAddress`), from being split.
        contents = re.sub(pattern, ';', contents)
        # Split each row via newline escape sequence.
        contents = contents.split('\n')
        # Remove double quotes from string objects and split the
        # contents by semicolon.
        contents = [content.strip().replace('\"', '').split(';')
                    for content in contents]
        headers = contents[0]
        return (headers, contents)

    @property
    def keys(self):
        """Return keys related to AWS billing."""
        pattern = r'^\d+-aws-billing-csv-[\d+]{4}-[\d+]{2}.csv$'
        for key in self.bucket.get_all_keys():
            if re.search(pattern, key.name):
                yield key

    def records(self, current=False):
        """Return each row of each AWS billing record as a dictionary
        object."""
        now = datetime.now()
        format = '%Y/%m/%d %H:%M:%S'
        for key in self.keys:
            contents = key.get_contents_as_string()
            (headers, contents) = self._parse_contents(contents)
            # Ignore the first line and any row that is not of type
            # `PayerLineItem`.
            for content in contents[1:]:
                content = dict(itertools.izip(headers, content))
                if content.get('RecordType') != 'PayerLineItem':
                    continue
                start_date = datetime.strptime(
                    content['BillingPeriodStartDate'], format
                )
                end_date = datetime.strptime(
                    content['BillingPeriodEndDate'], format
                )
                if current:
                    if start_date <= now <= end_date:
                        yield content
                else:
                    if start_date <= end_date <= now:
                        yield content

class Forecast(Billing):
    def __init__(self, service=None, **kwargs):
        super(Forecast, self).__init__(**kwargs)

    def records(self, service=None, current=False):
        """Return billing records given a specific time."""
        for content in super(Forecast, self).records(current=current):
            if service:
                if content['ProductCode'] == service:
                    yield content
            else:
                yield content

    def series(self, service=None, current=False):
        """Return Pandas series data for either the current month or
        prior months."""
        keys = ('BillingPeriodEndDate', 'ProductCode', 'ItemDescription',
                'TotalCost',)
        return pandas.Series(
            tuple(record.get(key) for key in keys)
            for record in self.records(service=service, current=current)
        )
