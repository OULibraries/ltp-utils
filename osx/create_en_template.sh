#!/bin/sh

## Create english language template based on current user account
## Directly inspired by Jason Watkins howto
## https://sites.sas.upenn.edu/jasonrw/blog/2013/03/create-custom-default-user-profile-os-x-107108

TEMPLATE_SOURCE=$USER

## Need to be root
sudo su

## Backup old default profile
cp -r /System/Library/User\ Template/English.lproj /System/Library/User\ Template/English.bak

## Remove old default profile
rm -rf /System/Library/User\ Template/English.lproj/*

## Add custom profile from user
rsync -av /Users/$TEMPLATE_SOURCE/* /System/Library/User\ Template/English.lproj/

## chown profile to root
chown -R root:wheel /System/Library/User\ Template/English.lproj/

## Remove Keychain
rm -rf  /System/Library/User\ Templates/English.lproj/Library/Keychains/*

## Repair permissions
diskutil repairPermissions /
