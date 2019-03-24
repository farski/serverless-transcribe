# This function is triggered by an S3 event when an object is created. It
# starts a transcription job with the media file, and sends a message about the
# job to an SQS queue.

import boto3
import uuid
import os

s3 = boto3.client('s3')
ses = boto3.client('ses')
sqs = boto3.client('sqs')
transcribe = boto3.client('transcribe')

s3_host = f"s3-{os.environ['AWS_REGION']}.amazonaws.com"


def get_s3_metadata(bucket, key):
    return s3.head_object(Bucket=bucket, Key=key)['Metadata']


def lambda_handler(event, context):
    # Generate a unique name for the job
    transcription_job_name = uuid.uuid4()

    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    print(f"Starting transcription job: {transcription_job_name}")
    print(f"Object: {bucket_name}/{object_key}")

    transcribe.start_transcription_job(
        TranscriptionJobName=f"{transcription_job_name}",
        LanguageCode='en-US',
        MediaFormat='mp3',
        Media={
            'MediaFileUri': f"https://{s3_host}/{bucket_name}/{object_key}"
        },
        OutputBucketName=os.environ['TRANSCRIPTIONS_OUTPUT_BUCKET'],
    )

    sqs.send_message(
        QueueUrl=os.environ['TRANSCRIPTION_JOB_SCAN_QUEUE_URL'],
        MessageBody=f"{transcription_job_name}",
        MessageAttributes={
            'MediaBucketName': {
                'DataType': 'String',
                'StringValue': bucket_name
            },
            'MediaObjectKey': {
                'DataType': 'String',
                'StringValue': object_key
            }
        }
    )

    media_metadata = get_s3_metadata(bucket_name, object_key)
    notification_email = media_metadata['email']

    ses.send_email(
        Source=os.environ['NOTIFICATION_SOURCE_EMAIL_ADDRESS'],
        Destination={
            'ToAddresses': [
                notification_email
            ]
        },
        Message={
            'Subject': {
                'Data': f"Transcription has started for {object_key}",
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': 'An email will be sent when it completes.',
                    'Charset': 'UTF-8'
                }
            }
        }
    )
