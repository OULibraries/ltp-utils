#!/bin/sh

## Create english language template based on specified account
## Directly inspired by Jason Watkins howto
## https://sites.sas.upenn.edu/jasonrw/blog/2013/03/create-custom-default-user-profile-os-x-107108
die () {
    echo >&2 "$@"
    exit 1
}

## need to be root
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

## user account required
[ "$#" -eq 1 ] || die "1 argument required, $# provided"

TEMPLATE_SOURCE=$1


## Backup old default profile
cp -r /System/Library/User\ Template/English.lproj /System/Library/User\ Template/English.bak

## Remove old default profile
rm -rf /System/Library/User\ Template/English.lproj/*

## Add custom profile from user
rsync -av /Users/$TEMPLATE_SOURCE/* /System/Library/User\ Template/English.lproj/

## chown profile to root
chown -R root:wheel /System/Library/User\ Template/English.lproj/

## Remove Keychain
rm -rf  /System/Library/User\ Template/English.lproj/Library/Keychains/*

## Repair permissions
diskutil repairPermissions /
