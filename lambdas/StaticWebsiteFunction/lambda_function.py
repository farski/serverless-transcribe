def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {'content-type': 'text/html'},
        'body': open('index.html', 'r', encoding='utf-8').read()
    }
