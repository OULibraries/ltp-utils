## aws notes

### Keepalived stuff
Conceptually cribbed from [Brandon Burton's](https://twitter.com/solarce)
[aws advent post](http://awsadvent.tumblr.com/post/105141640154/aws-advent-2014-high-availability-in-aws-with)



notify.sh requires aws-cli and goes in

/usr/libexec/keepalived/

make sure you do a restorcon afterwards

/sbin/restorecon -v -F /usr/libexec/keepalived/notify.sh


keepalived.conf goes in

/etc/keepalived/

Make sure you change ip addresses as appropriate.


### other stuff

prompt.sh goes in /etc/profile.d

sets the shell prompt to reflect the aws instance name.  centos kept resetting the hostname to the internal ip. This annoyed me.
