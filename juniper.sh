#!/bin/sh

# Grab the user session data from Juniper login and run openconnect
# Prerequisites:
# - Sudo, with the rights to openconnect and route
# - Firefox (it might be doable with Chrome but you'll need their greasemonkey equivalent, plus
#   I'm not sure where they dump local storage so you're on your own)
# - openconnect, at least version 7.06
# - sqlite3 (the command line client)
# - Install Greasemonkey script https://alexeymoseyev.wordpress.com/2014/10/29/junos-pulse-vpn-client-on-linux-two-phase-auth-64bit-how-to-make-it-all-work/
#   - Note you just need the Greasemonkey script
# - You may want to change the route commands at the end according to your setup
#   Personally I don't want my general internet traffic to run through some VPN server in
#   some other country, it makes latency ridiculous
#
# To login:
# - Login with your webbrowser (even if Java isn't installed)
#   - The greasemonkey script will ensure the DSID cookie gets dumped to the local storage database
# - Run this script
# - CTRL-C when done
#
# Update the variable below to your server name
SERVER=server.host.name

rserver=`echo -n $SERVER | rev`
dsid1=`echo "select value from webappsstore2 where originKey='$rserver.:https:443' and key='DSID';" | sqlite3 ~/.mozilla/firefox/*.default/webappsstore.sqlite`

# ensure we get the password immediately
sudo echo dsid=$dsid1
sudo openconnect --juniper -C "DSID=$dsid1" $SERVER &
# dirty hack to check 
sleep 5
sudo ip route del default
sudo ip route add default via 192.168.1.1 dev eth0
sudo ip route add 10.0.0.0/8 scope link dev tun0
wait
