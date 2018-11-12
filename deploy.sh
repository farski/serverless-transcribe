#!/bin/zsh
set -e

source ./.env
mkdir -p .deploy

# Copy Lambda code to S3
mkdir -p .deploy/lambdas
cd ./lambdas; find * -maxdepth 0 -type d|while read dirname; do cd "$dirname"; zip -r "$dirname" *; mv "$dirname".zip ../../.deploy/lambdas; cd ..; done; cd ..
aws s3 sync .deploy/ s3://$STACK_RESOURCES_BUCKET/$CLOUDFORMATION_STACK_NAME/ --acl private --region us-east-1

# Deploy CloudFormation stack
aws cloudformation deploy \
    --template-file ./serverless-transcribe.yml \
    --stack-name $CLOUDFORMATION_STACK_NAME \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        StackResourcesBucket=$STACK_RESOURCES_BUCKET \
        StackResourcesPrefix=$CLOUDFORMATION_STACK_NAME \
        UploadSecretAccessKey=$UPLOAD_SECRET_ACCESS_KEY \
        UploadAccessKeyId=$UPLOAD_ACCESS_KEY_ID \
        MediaBucketIdentifier=$MEDIA_BUCKET_IDENTIFIER \
        BasicAuthUsername=$BASIC_AUTH_USERNAME \
        BasicAuthPassword=$BASIC_AUTH_PASSWORD \
        NotificationSourceEmailAddress=$NOTIFICATION_SOURCE_EMAIL_ADDRESS

print '\nWebpage URL:'
aws cloudformation describe-stacks --stack-name $CLOUDFORMATION_STACK_NAME | grep "OutputValue" | sed 's/\"//g' | sed 's/ //g' | sed 's/,//g' | sed 's/OutputValue\://'
print '\n'
