# This function is triggered by an S3 event when an object is created. It
# starts a transcription job with the media file, and sends an email notifying
# the user that the job has started.

import boto3
import uuid
import os
import re
import urllib.parse

s3 = boto3.client('s3')
ses = boto3.client('ses')
transcribe = boto3.client('transcribe')

s3_host = f"s3-{os.environ['AWS_REGION']}.amazonaws.com"


def get_media_format(path):
    if re.search('.mp3$', path) is not None:
        return 'mp3'
    elif re.search('.mp4$', path) is not None:
        return 'mp4'
    elif re.search('.m4a$', path) is not None:
        return 'mp4'
    elif re.search('.wav$', path) is not None:
        return 'wav'
    elif re.search('.flac$', path) is not None:
        return 'flac'
    else:
        return 'mp3'


def get_s3_metadata(bucket, key):
    return s3.head_object(Bucket=bucket, Key=key)['Metadata']


def lambda_handler(event, context):
    # Generate a unique name for the job
    transcription_job_name = uuid.uuid4()

    bucket_name = event['Records'][0]['s3']['bucket']['name']
    _object_key = event['Records'][0]['s3']['object']['key']
    object_key = urllib.parse.unquote_plus(_object_key)

    print(f"Starting transcription job: {transcription_job_name}")
    print(f"Object: {bucket_name}/{object_key}")

    media_metadata = get_s3_metadata(bucket_name, object_key)
    notification_email = media_metadata['email']
    max_speaker_labels = int(media_metadata['maxspeakerlabels'])

    transcribe.start_transcription_job(
        TranscriptionJobName=f"{transcription_job_name}",
        LanguageCode='en-US',
        MediaFormat=get_media_format(object_key),
        Media={
            'MediaFileUri': f"https://{s3_host}/{bucket_name}/{object_key}"
        },
        Settings={
            'MaxSpeakerLabels': max_speaker_labels,
            'ShowSpeakerLabels': True
        },
        OutputBucketName=os.environ['TRANSCRIPTIONS_OUTPUT_BUCKET'],
    )

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
