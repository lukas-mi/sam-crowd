import os

import boto3


def new_client(sandbox=False):
    endpoint = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com' if sandbox else 'https://mturk-requester.us-east-1.amazonaws.com'

    return boto3.client(
        'mturk',
        endpoint_url=endpoint,
        region_name='us-east-1',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    )
