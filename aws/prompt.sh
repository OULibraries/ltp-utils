#!/bin/bash

# File: /etc/profile.d/prompt.sh
# Sets the prompt string for all users to include the name tag

# Config Stuff
REGION=us-east-1
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | grep "instanceId" | cut -d ":" -f 2 | tr "\
," " " | xargs)
SEC_ROLE=$(curl -s http://169.254.169.254/latest/meta-data/iam/info/ | grep InstanceProfileArn | awk -F" : " '{print $2}' | cut -d"\
:" -f 6  | cut -d "/" -f 2 |  sed 's/\",$//')

# Get the right credentials to ask for name tag
export AWS_ACCESS_KEY_ID=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/$SEC_ROLE | grep "AccessKeyId" \
				  | cut -d ":" -f 2 | tr "," " " | xargs)
export AWS_SECRET_ACCESS_KEY=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/$SEC_ROLE | grep "SecretAcc\
essKey" | cut -d ":" -f 2 | tr "," " " | xargs)
export AWS_SECURITY_TOKEN=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/$SEC_ROLE | grep "Token" | cut\
																    -d ":" -f 2 | tr "," " " | xargs)
export AWS_DELEGATION_TOKEN=$(curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/$SEC_ROLE | grep "Token" | c\
																      ut -d ":" -f 2 | tr "," " " | xargs)

# Get host name tag
aws configure set region $REGION
EC2_NAME=$(aws ec2 describe-tags --filters Name=resource-type,Values=instance Name=resource-id,Values=$INSTANCE_ID Name=key,Values=\
	       Name | grep -B 1 Name | grep -v Name | cut -d ":" -f 2 | tr "," " " | xargs)

# Set prompt string accordingly
export PS1='[\u@$EC2_NAME \w]\$ '
