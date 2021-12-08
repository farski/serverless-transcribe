# This function is triggered by API Gateway as an authorizer. It uses the HTTP
# basic auth Authorization header to permit access to API Gateway methods by
# returning a policy document when the credentials match those defined as stack
# parameters. The policy grants access to all paths belonging to the API
# Gateway.

import os
import base64


def lambda_handler(event, context):
    headers = event['headers']

    # Looks like: Authorization: Basic a1b2c3e4f5=
    base_64_credentials = headers['Authorization'].split(' ')[1]
    credentials = base64.b64decode(base_64_credentials).decode('utf-8')

    parts = credentials.split(':')
    username = parts[0]
    password = parts[1]

    policy_effect = 'Deny'

    u = os.environ['BASIC_AUTH_USERNAME']
    p = os.environ['BASIC_AUTH_PASSWORD']
    if username == u and password == p:
        policy_effect = 'Allow'

    return {
        'policyDocument': {
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': policy_effect,
                    'Resource': f"{event['methodArn'].split('/')[0]}/*"
                }
            ],
            'Version': '2012-10-17'
        }
    }
