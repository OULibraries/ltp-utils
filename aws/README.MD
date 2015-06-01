## aws notes

notify.sh goes in

/usr/libexec/keepalived/

make sure you do a restorcon afterwards

/sbin/restorecon -v -F /usr/libexec/keepalived/notify.sh


keepalived.conf goes in

/etc/keepalived/

Make sure you change ip addresses as appropriate.
