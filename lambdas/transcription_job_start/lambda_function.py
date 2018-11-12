# This function is triggered by an S3 event when an object is created. It
# starts a transcription job with the media file, and sends a message about the
# job to an SQS queue.

import boto3
import uuid
import os

s3 = boto3.client('s3')
sqs = boto3.client('sqs')
transcribe = boto3.client('transcribe')


def lambda_handler(event, context):
    transcription_job_name = uuid.uuid4()

    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    transcribe.start_transcription_job(
        TranscriptionJobName=f"{transcription_job_name}",
        LanguageCode='en-US',
        MediaFormat='mp3',
        Media={
            # TODO Don't hard code the region
            'MediaFileUri': f"https://s3-us-east-1.amazonaws.com/{bucket_name}/{object_key}"
        },
        OutputBucketName=os.environ['TRANSCRIPTIONS_OUTPUT_BUCKET'],
    )

    # TODO This is probably not needed
    s3.put_object_tagging(
        Bucket=bucket_name,
        Key=object_key,
        Tagging={
            'TagSet': [
                {
                    'Key': 'TranscriptionJobName',
                    'Value': f"{transcription_job_name}"
                },
            ]
        }
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
