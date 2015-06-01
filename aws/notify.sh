#!/bin/bash

# The virtual interface for keepalived
VIP=secondary-private-ip
# The Elastic IP you want to use
EIP=an-elastic-ip
# The region for all of this
REGION=us-east-1

PATH=/usr/local/bin:/usr/bin:/bin:/sbin:$PATH
INSTANCE_ID=`curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | grep "instanceId" | cut -d ":" -f 2 | tr "," " " | xargs`
export AWS_ACCESS_KEY_ID=`curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/lib-amz-http-ha | grep "AccessKeyId" | cut -d ":" -f 2 | tr "," " " | xargs`
export AWS_SECRET_ACCESS_KEY=`curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/lib-amz-http-ha | grep "SecretAccessKey" | cut -d ":" -f 2 | tr "," " " | xargs`
export AWS_SECURITY_TOKEN=`curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/lib-amz-http-ha | grep "Token" | cut -d ":" -f 2 | tr "," " " | xargs`
aws configure set region $REGION

NIC_ID=`aws ec2 describe-network-interfaces --filters Name=attachment.instance-id,Values=$INSTANCE_ID | grep -m 1 "NetworkInterfaceId" | cut -d ":" -f 2 | tr "," " " | xargs`
ASSOCIATION_ID=`aws ec2 describe-addresses | grep -B 6 -A 3 $EIP | grep "AssociationId" | cut -d ":" -f 2 | tr "," " " | xargs`
ALLOCATION_ID=`aws ec2 describe-addresses | grep -B 6 -A 3 $EIP | grep "AllocationId" | cut -d ":" -f 2 | tr "," " " | xargs`
aws ec2 assign-private-ip-addresses --network-interface-id $NIC_ID --private-ip-addresses $VIP --allow-reassignment
aws ec2 disassociate-address --association-id $ASSOCIATION_ID
aws ec2 associate-address --allocation-id $ALLOCATION_ID  --instance-id $INSTANCE_ID --private-ip-address $VIP --allow-reassociation
