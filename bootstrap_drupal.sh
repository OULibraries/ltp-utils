#!/bin/sh
## Deploy from drush make

# Owner and group for site path
SITESOWNER=apache:apache

# Set path and sudo string
PATH=/usr/local/bin:/usr/bin:/bin:/sbin
SUDO=''
if (( $EUID != 0 )); then
    SUDO='sudo'
fi

## Require argument
if [ ! -z "$1" ]
then
  SITEPATH=$1
  echo "Processing $SITEPATH"
else
  echo "Requires site path (eg. /srv/sample) as argument"
  exit 1;
fi

# Get root DB password
echo -n Root DB Password:
read -s ROOTDBPSSWD
echo

# Generate Drupal DB password
DBPSSWD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)

if [[ -e $SITEPATH ]]; then
    echo "$SITEPATH already exists!"
    exit 1
fi

## Make the parent directory
$SUDO mkdir -p $SITEPATH

## Grab the basename of the site to use in a few places.
SITE=`basename $SITEPATH`

## Build from drush make
$SUDO drush dl drupal --drupal-project-rename=drupal --destination=$SITEPATH || exit 1;

##  Move the default site out of the build. This makes updates easier later.
$SUDO mv $SITEPATH/drupal/sites/default $SITEPATH/

## Link default site folder
$SUDO ln -s $SITEPATH/default $SITEPATH/drupal/sites/default

## Setup settings.php
read -d '' SETTINGSPHP <<- EOF
\$databases = array (
  'default' =>
  array (
    'default' =>
    array (
      'database' => 'drupal_$SITE',
      'username' => '$SITE',
      'password' => '$DBPSSWD',
      'host' => 'localhost',
      'port' => '',
      'driver' => 'mysql',
      'prefix' => '',
    ),
  ),
);
EOF

## Write out settings.php
$SUDO cp $SITEPATH/default/default.settings.php $SITEPATH/default/settings.php
echo "$SETTINGSPHP" >> $SITEPATH/default/settings.php

## Create the Drupal database
$SUDO drush sql-create --db-su=root --db-su-pw=$ROOTDBPSSWD -r $SITEPATH/drupal || exit 1;

## Do the Drupal install
$SUDO drush -y -r $SITEPATH/drupal site-install --site-name=$SITE || exit 1;

## Make the apache config
sudo sed "s/__SITE_DIR__/$SITE/g" /etc/httpd/conf.d/template_init_oulib_drupal > /etc/httpd/conf.d/srv_$SITE.conf

# Set SELinux and owner
$SUDO chcon -R -t  httpd_sys_content_t $SITEPATH
$SUDO chown -R $SITESOWNER $SITEPATH

## Set perms - allows group write
$SUDO find $SITEPATH -type d -exec chmod u=rwx,g=rwx,o= '{}' \;
$SUDO find $SITEPATH -type f -exec chmod u=rw,g=rw,o= '{}' \;

$SUDO service httpd configtest || exit 1;
$SUDO service httpd reload || exit 1;
