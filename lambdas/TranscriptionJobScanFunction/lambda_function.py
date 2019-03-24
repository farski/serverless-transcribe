# This function is subscribed to an SQS queue that has messages corresponding
# to new and in-progress transcription jobs. The messages are delayed. When
# a message is sent to the function, the status of the corresponding job is
# checked. If the job is still in progress, it is sent back to the queue (as a
# new message). If the job has completed, an email containing the transcript
# is sent. The recipient is garnered from the metadata of the media file that
# was used to create the transcription job.

import boto3
import json
import os

s3_resource = boto3.resource('s3')

s3 = boto3.client('s3')
ses = boto3.client('ses')
sqs = boto3.client('sqs')
transcribe = boto3.client('transcribe')


def get_s3_metadata(bucket, key):
    return s3.head_object(Bucket=bucket, Key=key)['Metadata']


def get_transcript_data(transcription_job_name):
    job = transcribe.get_transcription_job(
        TranscriptionJobName=transcription_job_name
    )['TranscriptionJob']

    if job['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_file_uri = job['Transcript']['TranscriptFileUri']
        transcript_path = transcript_file_uri.split("amazonaws.com/", 1)[1]

        transcript_bucket = transcript_path.split('/', 1)[0]
        transcript_key = transcript_path.split('/', 1)[1]

        s3_object = s3_resource.Object(transcript_bucket, transcript_key).get()
        transcript_json = s3_object['Body'].read().decode('utf-8')
        transcript_data = json.loads(transcript_json)

        return transcript_data
    else:
        return None


def lambda_handler(event, context):
    # `record` is the SQS message enqueued by the JobStart function.
    # The message body is the the transcription job name, and the message
    # attributes include the bucket name and object key for the object that
    # triggered the job.
    record = event['Records'][0]

    message_attributes = record['messageAttributes']
    media_bucket_name = message_attributes['MediaBucketName']['stringValue']
    media_object_key = message_attributes['MediaObjectKey']['stringValue']

    transcription_job_name = record['body']
    transcription_job_data = get_transcript_data(transcription_job_name)

    if transcription_job_data is not None:
        # If the job is complete, fetch the email to where the the transcript
        # should be sent, and send the email
        print(f"Transcription job complete: {transcription_job_name}")

        transcripts = transcription_job_data['results']['transcripts']
        transcript = transcripts[0]['transcript']

        # The notification email was set as metadata on the object when it was
        # first created (x-amz-meta-email)
        media_metadata = get_s3_metadata(media_bucket_name, media_object_key)
        notification_email = media_metadata['email']

        print(f"Sending notification to {notification_email}")

        ses.send_email(
            Source=os.environ['NOTIFICATION_SOURCE_EMAIL_ADDRESS'],
            Destination={
                'ToAddresses': [
                    notification_email
                ]
            },
            Message={
                'Subject': {
                    'Data': 'Transcript is ready',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': transcript,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
    else:
        # Put the job back on the queue to get checked again in several minutes
        sqs.send_message(
            QueueUrl=os.environ['TRANSCRIPTION_JOB_SCAN_QUEUE_URL'],
            MessageBody=transcription_job_name,
            MessageAttributes={
                'MediaBucketName': {
                    'DataType': 'String',
                    'StringValue': media_bucket_name
                },
                'MediaObjectKey': {
                    'DataType': 'String',
                    'StringValue': media_object_key
                }
            }
        )
