#!/bin/bash
set -e

source ./.env
mkdir -p .deploy

# Check Versioning status for resources bucket
bucket_versioning=`aws s3api get-bucket-versioning --bucket "$STACK_RESOURCES_BUCKET" --output text --query 'Status'`
if [ "$bucket_versioning" != "Enabled" ]
then
        echo "Bucket versioning must be enabled for the stack resources bucket"
        return 1
fi

# Copy Lambda code to S3
version_suffix="S3ObjectVersion"
mkdir -p .deploy/lambdas
cd ./lambdas
while read dirname
do
        cd "$dirname"
        zip -r "$dirname" *
        mv "${dirname}.zip" ../../.deploy/lambdas
        version_id=`aws s3api put-object --bucket "$STACK_RESOURCES_BUCKET" --key "${CLOUDFORMATION_STACK_NAME}/lambdas/${dirname}.zip" --acl private --body ../../.deploy/lambdas/"$dirname".zip --output text --query 'VersionId'`
        declare "${dirname}_${version_suffix}"="$version_id"
        cd ..
done < <(find * -maxdepth 0 -type d)
cd ..

# Deploy CloudFormation stack
aws cloudformation deploy \
        --template-file ./serverless-transcribe.yml \
        --stack-name "$CLOUDFORMATION_STACK_NAME" \
        --capabilities CAPABILITY_IAM \
        --parameter-overrides \
                StackResourcesBucket="$STACK_RESOURCES_BUCKET" \
                StackResourcesPrefix="$CLOUDFORMATION_STACK_NAME" \
                MediaBucketIdentifier="$MEDIA_BUCKET_IDENTIFIER" \
                BasicAuthUsername="$BASIC_AUTH_USERNAME" \
                BasicAuthPassword="$BASIC_AUTH_PASSWORD" \
                NotificationSourceEmailAddress="$NOTIFICATION_SOURCE_EMAIL_ADDRESS" \
                TranscriptionJobStartFunctionS3ObjectVersion="$TranscriptionJobStartFunction_S3ObjectVersion" \
                WebsiteApiFunctionS3ObjectVersion="$WebsiteApiFunction_S3ObjectVersion" \
                StaticWebsiteFunctionS3ObjectVersion="$StaticWebsiteFunction_S3ObjectVersion" \
                StaticWebsiteAuthorizerFunctionS3ObjectVersion="$StaticWebsiteAuthorizerFunction_S3ObjectVersion" \
                TranscriptionJobStateChangeFunctionS3ObjectVersion="$TranscriptionJobStateChangeFunction_S3ObjectVersion"

echo
echo 'Webpage URL:'
aws cloudformation describe-stacks --stack-name "$CLOUDFORMATION_STACK_NAME" | grep "OutputValue" | sed 's/\"//g' | sed 's/ //g' | sed 's/,//g' | sed 's/OutputValue\://'
echo
