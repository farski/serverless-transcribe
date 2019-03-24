#!/bin/zsh
set -e

source ./.env
mkdir -p .deploy

# Check Versioning status for resources bucket
bucket_versioning=`aws s3api get-bucket-versioning --bucket $STACK_RESOURCES_BUCKET --output text --query 'Status'`
if [ $bucket_versioning != "Enabled" ]
then
        echo "Bucket versioning must be enabled for the stack resources bucket"
        return 1
fi

# Copy Lambda code to S3
mkdir -p .deploy/lambdas
cd ./lambdas
find * -maxdepth 0 -type d|while read dirname
do
        cd "$dirname"
        zip -r "$dirname" *
        mv "$dirname".zip ../../.deploy/lambdas
        version_id=`aws s3api put-object --bucket $STACK_RESOURCES_BUCKET --key $CLOUDFORMATION_STACK_NAME/lambdas/"$dirname".zip --acl private --body ../../.deploy/lambdas/"$dirname".zip --output text --query 'VersionId'`
        declare ${dirname}S3ObjectVersion="$version_id"
        cd ..
done
cd ..

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
                NotificationSourceEmailAddress=$NOTIFICATION_SOURCE_EMAIL_ADDRESS \
                TranscriptionJobStartFunctionS3ObjectVersion=$TranscriptionJobStartFunctionS3ObjectVersion \
                TranscriptionJobScanFunctionS3ObjectVersion=$TranscriptionJobScanFunctionS3ObjectVersion \
                WebsiteApiFunctionS3ObjectVersion=$WebsiteApiFunctionS3ObjectVersion \
                StaticWebsiteFunctionS3ObjectVersion=$StaticWebsiteFunctionS3ObjectVersion \
                StaticWebsiteAuthorizerFunctionS3ObjectVersion=$StaticWebsiteAuthorizerFunctionS3ObjectVersion

print '\nWebpage URL:'
aws cloudformation describe-stacks --stack-name $CLOUDFORMATION_STACK_NAME | grep "OutputValue" | sed 's/\"//g' | sed 's/ //g' | sed 's/,//g' | sed 's/OutputValue\://'
print '\n'
