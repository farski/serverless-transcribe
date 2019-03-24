# This function is triggered by API Gateway as an authorizer. It uses the HTTP
# basic auth Authorization header to permit access to API Gateway methods by
# returning a policy document when the credentials match those defined as stack
# parameters.

import os
import base64


def lambda_handler(event, context):
    headers = event['headers']

    if headers['Authorization'] is None:
        return

    base_64_credentials = headers['Authorization'].split(' ')[1]
    credentials = base64.b64decode(base_64_credentials).decode('utf-8')

    username = credentials.split(':')[0]
    password = credentials.split(':')[1]

    if username != os.environ['BASIC_AUTH_USERNAME']:
        return
    if password != os.environ['BASIC_AUTH_PASSWORD']:
        return

    return {
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Allow',
                    'Resource': event['methodArn']
                }
            ]
        }
    }
