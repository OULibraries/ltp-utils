#!/bin/sh
SUDO=''
if (( $EUID != 0 )); then
    SUDO='sudo'
fi

echo "Please enter a new ssh username"
read USER

echo "Please enter a secondary user group, if desired:"
echo "e.g. if you would like the user to have sudo access"
echo "then you would enter \"wheel\"."
echo "otherwise, just press enter."
read GROUP

if [[ $GROUP = "" ]]
then
  $SUDO useradd $USER
else
  $SUDO useradd -G $GROUP $USER
fi

$SUDO mkdir /home/$USER/.ssh

echo "Enter the comment for the public key provided by the user:"
read PUBKEYCOMMENT

echo "Paste the rsa public key provided by the user:"
echo "It should not include the comment or the"
echo "ssh-rsa preamble, just random characters"
echo "terminated by == on a single line."
read PUBKEY

$SUDO echo "---- BEGIN SSH2 PUBLIC KEY ----" >> /home/$USER/.ssh/authorized_keys
$SUDO echo "Comment: \"$PUBKEYCOMMENT\"" >> /home/$USER/.ssh/authorized_keys
$SUDO echo -e "ssh-rsa $PUBKEY" >> /home/$USER/.ssh/authorized_keys
$SUDO echo "---- END SSH2 PUBLIC KEY ----" >> /home/$USER/.ssh/authorized_keys
$SUDO chown -R $USER:$USER /home/$USER/.ssh
$SUDO chmod -R 700 /home/$USER/.ssh
$SUDO echo -e "$USER\n" | $SUDO passwd $USER --stdin
