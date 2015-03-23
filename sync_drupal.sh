#!/bin/sh
## Sync Drupal files & DB from source host

# Owner and group for site path
SITESOWNER=apache:apache

# Writable dir on both local and souce hosts
TEMPDIR=/var/local/backups/drupal/temp

# Set path and sudo string
PATH=/usr/local/bin:/usr/bin:/bin:/sbin
SUDO=''
if (( $EUID != 0 )); then
    SUDO='sudo'
fi

## Require argument
if [ ! -z "$1" ] && [ ! -z "$2" ]
then
  SITEPATH=$1
  SRCHOST=$2
  echo "Syncing $SITEPATH content from $SRCHOST"
else
  echo "Requires site path (eg. /srv/sample) and source host as argument"
  exit 1;
fi

## Grab the basename of the site to use in a few places.
SITE=`basename $SITEPATH`

#from target
rsync -a --ignore-times $SRCHOST:$SITEPATH/default/files $SITEPATH/default/
#copy db
ssh -A $SRCHOST drush -r $SITEPATH/drupal sql-dump --result-file=$TEMPDIR/drupal_$SITE.sql
rsync $SRCHOST:$TEMPDIR/drupal_$SITE.sql $TEMPDIR/
sudo drush sql-cli -r $SITEPATH/drupal < $TEMPDIR/drupal_$SITE.sql || exit 1;
echo "Database synced"

## Set perms of default site dir
$SUDO chcon -R -t  httpd_sys_content_t $SITEPATH/default
$SUDO chown -R $SITESOWNER $SITEPATH/default
$SUDO find $SITEPATH/default -type d -exec chmod u=rwx,g=rx,o= '{}' \;
$SUDO find $SITEPATH/default -type f -exec chmod u=rw,g=r,o= '{}' \;
