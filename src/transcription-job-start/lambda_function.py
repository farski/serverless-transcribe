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
    if re.search('.wav$', path) is not None:
        return 'wav'
    elif re.search('.flac$', path) is not None:
        return 'flac'
    elif re.search('.amr$', path) is not None:
        return 'amr'
    elif re.search('.3ga$', path) is not None:
        return 'amr'
    elif re.search('.mp3$', path) is not None:
        return 'mp3'
    elif re.search('.mp4$', path) is not None:
        return 'mp4'
    elif re.search('.m4a$', path) is not None:
        return 'mp4'
    elif re.search('.oga$', path) is not None:
        return 'ogg'
    elif re.search('.ogg$', path) is not None:
        return 'ogg'
    elif re.search('.opus$', path) is not None:
        return 'ogg'
    elif re.search('.webm$', path) is not None:
        return 'webm'
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
    channel_identification = media_metadata['channelidentification']
    language_code = media_metadata['languagecode']
    max_speaker_labels = int(media_metadata['maxspeakerlabels'])

    transcription_job_settings = {
        'ChannelIdentification': channel_identification == 'On',
        'ShowSpeakerLabels': channel_identification != 'On'
    }

    job_params = {
        'TranscriptionJobName': f"{transcription_job_name}",
        'MediaFormat': get_media_format(object_key),
        'Media': {
            'MediaFileUri': f"https://{s3_host}/{bucket_name}/{object_key}"
        },
        'Settings': transcription_job_settings,
        'OutputBucketName': os.environ['TRANSCRIPTIONS_OUTPUT_BUCKET'],
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'serverless-transcribe'
            }
        ]
    }

    if language_code == 'IdentifyLanguage':
        job_params['IdentifyLanguage'] = True
    else:
        job_params['LanguageCode'] = language_code

    if channel_identification != 'On':
        transcription_job_settings['MaxSpeakerLabels'] = max_speaker_labels

    if len(os.environ['JOB_TAG_KEY']) > 0 and len(os.environ['JOB_TAG_VALUE']) > 0:
        job_params['Tags'].append({
                'Key': os.environ['JOB_TAG_KEY'],
                'Value': os.environ['JOB_TAG_VALUE']
        })

    print(f"Job parameters: {job_params}")

    transcribe.start_transcription_job(**job_params)

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
