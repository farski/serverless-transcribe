# The static webpage used to upload media files for transcriptions uploads the
# files directly to S3. In order for this to work, the POST request made by the
# form on the website to the S3 bucket URL must include several things. These
# include a base 64 encoded copy of the policy used to control uploads to the
# bucket, as well as a signature created using the V4 signing method. There are
# some other things S3 expects in the POST data as well. This function returns
# a JSON object containing those data so the webpage has access to those
# values. It backs an API Gateway endpoint.

import json
import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta

AMZ_ALGORITHM = 'AWS4-HMAC-SHA256'


# Returns information about the values used to derive the signing key used to
# sign the POST policy for S3 requests
# In the format:
# <your-access-key-id>/<date>/<aws-region>/<aws-service>/aws4_request
# eg: AKIAIOSFODNN7EXAMPLE/20130728/us-east-1/s3/aws4_request
def signing_credentials(signing_time):
    access_key_id = os.environ['UPLOAD_ACCESS_KEY_ID']
    date_stamp = signing_time.strftime('%Y%m%d')
    region = os.environ['AWS_REGION']

    return f"{access_key_id}/{date_stamp}/{region}/s3/aws4_request"


# Returns an POST policy used for making authenticated POST requests to S3
# https://docs.aws.amazon.com/AmazonS3/latest/API/sigv4-HTTPPOSTConstructPolicy.html
def s3_post_policy(signing_time, ttl=60):
    expiration_date = datetime.utcnow() + timedelta(minutes=ttl)

    print(f"== EXPIRES == {expiration_date.strftime('%Y-%m-%dT%H:%M:%SZ')}")

    return {
        'expiration': expiration_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'conditions': [
            {'bucket': os.environ['MEDIA_BUCKET']},

            {'x-amz-algorithm': AMZ_ALGORITHM},
            {'x-amz-credential': signing_credentials(signing_time)},
            {'x-amz-date': signing_time.strftime('%Y%m%dT%H%M%SZ')},

            ["starts-with", "$success_action_redirect", ""],
            ["starts-with", "$x-amz-meta-email", ""],
            ["starts-with", "$x-amz-meta-maxspeakerlabels", ""],
            ["starts-with", "$key", "audio/"],
            ["starts-with", "$Content-Type", "audio/"]
        ]
    }


# Returns a HMAC-SHA256 hash of the given message, using the given key
def digest(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


# Derives a signing key for an AWS V4 signature
# See step 1: https://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html
def aws_v4_signing_key(access_key, date_stamp, region, service):
    date_key = digest(('AWS4' + access_key).encode('utf-8'), date_stamp)
    date_region_key = digest(date_key, region)
    date_region_service_key = digest(date_region_key, service)

    signing_key = digest(date_region_service_key, 'aws4_request')

    return signing_key


# Returns an AWS V4 signature for the given string. Generates a signing key
# for S3 in the Lambda execution region
# See step 2: https://docs.aws.amazon.com/general/latest/gr/sigv4-calculate-signature.html
def aws_v4_signature(signing_time, string_to_sign):
    access_key = os.environ['UPLOAD_SECRET_ACCESS_KEY']
    date_stamp = signing_time.strftime('%Y%m%d')
    region = os.environ['AWS_REGION']
    service = 's3'

    signing_key = aws_v4_signing_key(access_key, date_stamp, region, service)

    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    return signature


def lambda_handler(event, context):
    signing_time = datetime.utcnow()
    print("Generating POST policy and AWS V4 signature.")
    print(f"== SIGNED ===  {signing_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")

    # A POST policy for S3 requests
    post_policy = s3_post_policy(signing_time)

    post_policy_json = json.dumps(post_policy)
    post_policy_json_b64 = base64.b64encode(post_policy_json.encode('utf-8')).decode('utf-8')

    # An AWS V4 signature of the POST policy
    policy_signature = aws_v4_signature(signing_time, post_policy_json_b64)

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'amz_algorithm': AMZ_ALGORITHM,
            'amz_credential': signing_credentials(signing_time),
            'amz_date': signing_time.strftime('%Y%m%dT%H%M%SZ'),
            'base64_policy': post_policy_json_b64,
            'bucket_domain_name': os.environ['MEDIA_BUCKET_DOMAIN_NAME'],
            'signature': policy_signature
        })
    }
