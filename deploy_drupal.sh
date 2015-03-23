#!/bin/sh
## Deploy drupal site from drush make

SITESOWNER=apache:apache                        # unix owner and group of site path.
## Don't edit below here.
# Require arguments
if [ ! -z "$1" ] && [ ! -z "$2" ]
then
  SITEPATH=$1
  MAKEFILE=$2
  echo "Deploying $MAKEFILE to $SITEPATH"
else
  echo "Requires site path (eg. /srv/sample) and makefile as argument"
  exit 1;
fi

PATH=/usr/local/bin:/usr/bin:/bin:/sbin
SUDO=''
if (( $EUID != 0 )); then
    SUDO='/usr/bin/sudo'
fi

## Build from drush make
$SUDO drush make $MAKEFILE $SITEPATH/drupal_build || exit 1;

## Delete default site in the build
$SUDO rm -rf $SITEPATH/drupal_build/sites/default

## Link default site folder
$SUDO chcon -R -t  httpd_sys_content_t $SITEPATH/default
$SUDO chown -R $SITESOWNER $SITEPATH/default
$SUDO ln -s /srv/lib/default $SITEPATH/drupal_build/sites/default

## Set perms of build dir
$SUDO chcon -R -t  httpd_sys_content_t $SITEPATH/drupal_build
$SUDO chown -R $SITESOWNER $SITEPATH/drupal_build
$SUDO find $SITEPATH/drupal_build -type d -exec chmod u=rwx,g=rx,o= '{}' \;
$SUDO find $SITEPATH/drupal_build -type f -exec chmod u=rw,g=r,o= '{}' \;

## Now that everything is ready, do the swap
$SUDO rm -rf $SITEPATH/drupal_bak
$SUDO mv $SITEPATH/drupal $SITEPATH/drupal_bak
$SUDO mv $SITEPATH/drupal_build $SITEPATH/drupal

## Clear the caches
$SUDO drush cc all -r $SITEPATH/drupal || exit 1;

## Don't talk to yourself, Drupal -- kthx logan
$SUDO drush eval  'variable_set('drupal_http_request_fails', 0)' -r $SITEPATH/drupal || exit 1;
