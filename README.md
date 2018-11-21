# serverless-transcribe

A simple UI for [Amazon Transcribe](https://aws.amazon.com/transcribe/)

## How it Works

Once the project has been launched in [CloudFormation](https://aws.amazon.com/cloudformation/), you will have access to a webpage that allows users to upload audio files. The page uploads the files directly to [S3](https://aws.amazon.com/s3/). The S3 bucket is configured to watch for audio files. When it sees new audio files, an [AWS Lambda](https://aws.amazon.com/lambda/) function is invoked, which starts a transcription job.

Periodically, after each job has started, another Lambda function checks on the job's status. Once it sees that a job has completed, the raw transcript is extracted from the job results, and is emailed to the user who uploaded the file.

The webpage is protected by HTTP Basic authentication, with a single set of credentials that you set when launching the stack. This is handled by an authorizer on the [API Gateway](https://aws.amazon.com/api-gateway/), and could be extended to allow for more complicated authorization schemes.

Amazon Transcribe currently has file limits of 2 hours and 1 GB.

### AWS Costs

The cost of running and using this project are almost entirely based on usage. Media files uploaded to S3 are set to expire after one day, and the resulting files in the transcripts bucket expire after 30 days. The Lambda functions have no fixed costs, so you will only be charged when they are invoked. Amazon Transcribe is "[pay-as-you-go](https://aws.amazon.com/transcribe/pricing/) based on the seconds of audio transcribed per month".

One Lambda function has an [SQS](https://aws.amazon.com/sqs/) event source, which uses long polling to watch for messages. The function is only called when messages are availabe in the queue, but the polling will generate API calls to SQS on a fairly continous basis. Please see the end of this [blog post](https://aws.amazon.com/blogs/aws/aws-lambda-adds-amazon-simple-queue-service-to-supported-event-sources/) for more information. (At 1 request per second, or roughly 2.8 million requests per month, the cost would be about $1 per month. Long polling will not generate nearly that many requests.)

Most resources created from the CloudFormation template include a `Project` resource tag, which you can use for cost allocation. Unfortunately Amazon Transcribe jobs cannot be tracked this way.

## How to Use

The project is organized using a CloudFormation [template](https://github.com/farski/serverless-transcribe/blob/master/serverless-transcribe.yml). Launching a stack from this template will create all the resources necessary for the system to work.

### Requirements

- The stack must be launched in an AWS region that supports [SES](https://aws.amazon.com/ses/). There aren't many of these, unfortunately. The addresses that SES will send to and from are determined by your SES domain verification and sandboxing status.
- There must be a pre-existing S3 bucket where resources (like Lambda function code) needed to launch the stack can be found. This can be any bucket that CloudFormation will have read access to when launching the stack (based on the role used to execute the launch).

### Using the Deploy Script

Included in this project is a [deploy script](https://github.com/farski/serverless-transcribe/blob/master/deploy.sh). Launching and updating the stack using this script is probably easier than using the AWS Console. In order to use the script, create a `.env` file in the repository directory (look at `.env.example` for reference), and run `./deploy.sh` (You may need to `chmod +x deploy.sh` prior to running the script.)

The deploy script will zip all the files in the `lambdas/` directory, and push the zip files to S3 so that CloudFormation will have access to the code when creating the Lambda functions. The S3 destination is determined by the value of the `STACK_RESOURCES_BUCKET` environment variable (which is also passed into the stack as a stack parameter).

**Please note** that the template expects Lambda function code zip files' object keys to be prefixed with the stack's name. For example, if your `STACK_RESOURCES_BUCKET=my_code_bucket`, and you name the stack `my_transcription_app`, CloudFormation will look for a file such as:

```
s3://my_code_bucket/my_transcription_app/lambdas/transcription_job_scan.zip
```

The deploy script will put files in the correct place in S3. If you chose to launch the stack through the Console you will need to create the zip files yourself, and ensure they end up in the correct bucket with the correct prefix.

The `UPLOAD_ACCESS_KEY` ID and secret are used to sign the upload requests the webpage makes to S3. The access key you provide must have the ability to do that.

Once the deploy script has finished running, it will print the URL for the upload webpage. You should be able to visit that page, enter the HTTP basic auth credentials you set, and upload a file for transcription.

Currently the deploy script will not push Lambda code changes to the deployed functions. The code will be pushed to S3, but CloudFormation will not update the function from the newer zip file. (WIP)
