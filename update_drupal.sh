#!/bin/bash
cd /
/usr/bin/sudo find -path "./srv/*/drupal/sites/*/settings.php" | while read -r SITE ; do
  PATH=`echo $SITE | /bin/sed -e "s,^.\(.*/drupal\)\(.*\),\1,g"`
  /usr/bin/sudo /bin/cp $PATH/.htaccess /tmp/
  /usr/bin/sudo /usr/bin/drush up -y --security-only -r $PATH
  /usr/bin/sudo /bin/cp /tmp/.htaccess $PATH/
  /usr/bin/sudo /bin/rm /tmp/.htaccess
done

/usr/bin/sudo /bin/chown -R apache:apache /srv
/usr/bin/sudo /sbin/service httpd restart
