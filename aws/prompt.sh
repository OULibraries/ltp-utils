#!/bin/bash
REGION=us-east-1
INSTANCE_ID=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | grep "instanceId" | cut -d ":" -f 2 | tr "," " " | xargs`

export AWS_ACCESS_KEY_ID=`curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/lib-amz-http-ha | grep "AccessKeyId" | cut -d ":" -f 2 | tr "," " " | xargs`
export AWS_SECRET_ACCESS_KEY=`curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/lib-amz-http-ha | grep "SecretAccessKey" | cut -d ":" -f 2 | tr "," " " | xargs`
export AWS_SECURITY_TOKEN=`curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/lib-amz-http-ha | grep "Token" | cut -d ":" -f 2 | tr "," " " | xargs`
export AWS_DELEGATION_TOKEN=`curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/lib-amz-http-ha | grep "Token" | cut -d ":" -f 2 | tr "," " " | xargs`

aws configure set region $REGION
EC2_NAME=`aws ec2 describe-tags --filters Name=resource-type,Values=instance Name=resource-id,Values=$INSTANCE_ID Name=key,Values=Name | grep -B 1 Name | grep -v Name | cut -d ":" -f 2 | tr "," " " | xargs`
export PS1='[\u@$EC2_NAME \w]\$ '
