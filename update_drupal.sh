#!/bin/bash
## Searches for any Drupal installs in /srv,
## updates them, resets ownership, then restarts apache.
SUDO=''
if (( $EUID != 0 )); then
    SUDO='/usr/bin/sudo'
fi
CHOWN=/bin/chown
CHMOD=/bin/chmod
CP=/bin/cp
DRUSH=/usr/bin/drush
SERVICE=/sbin/service

cd /
$SUDO find -path "./srv/*/drupal/sites/*/settings.php" | while read -r SITE ; do
  PATH=`echo $SITE | /bin/sed -e "s,^.\(.*/drupal\)\(.*\),\1,g"`
  printf "Checking $PATH\n"
  $SUDO $CP $PATH/.htaccess /tmp/
  $SUDO $DRUSH rf -r $PATH
  $SUDO $DRUSH up -y --security-only -r $PATH
  $SUDO $CP /tmp/.htaccess $PATH/
  $SUDO /bin/rm /tmp/.htaccess
  $SUDO $CHMOD -R 775 $PATH
  printf "\n\n"
done

$SUDO $CHOWN -R apache:apache /srv
$SUDO $SERVICE httpd restart
