# Purpose

This is a small project which is meant to help people login on Juniper's Network Connect
platform when using some odd two-factor authentication system.

I've specifically tested Duo, but possibly it works with some other hardware tokens.

Yes, one can use a 32-bit browser and a 32-bit Java plugin to get Juniper to work on
non-Windows platforms.  It takes tons of ram, and for some reason stopped working after
a kernel upgrade, so I got fed up and started using openconnect.  It works much better.

# Requirements

* Python 3.5+ (possibly works on older Python platforms, not sure)
* MechanicalSoup 0.4.0+
* OpenConnect 7.06+
* Linux. This may work on other platforms (notably Mac, or even Windows) but I'm not
  100% sure it will, especially when invoking the openconnect subprocess.
* Unless you pass --no-routes every time, you'll need the "ip" command line
  utility in your path to set routes post-connect.  Note that obviously that
  won't work in Windows.
* Root access, or sudo access to the script.

# Installation

Just put it in your PATH and chmod +x the script.  
If you want to install requirements, you can use

```
pip3 install -r requirements.txt
```

from the source directory.

You may want to edit the first few lines of the script to set some default routes
and whatnot.  Yes, I should be using openconnect's vpn script support.

# Usage

Please see the output of `juniper-openconnect.py --help` for more details.  You'll
need to run it as root or through sudo.

Once you're logged in, press enter to log out.

Beware though that the script is not yet very smart and if it finds that you
have other sessions logged in, *it will close all of them*.

# The juniper.sh shell script

If you can't get it to work, there's hope!  There's a hack you can use if you have 
Firefox and are willing to run a GreaseMonkey script.  See the comments at the top of
the juniper.sh shell script.

Basically it works like this: you login using the usual browser interface.  Even though
you may not be able to get the Java client to run, a cookie gets set through the web
interface containing the session ID.  The GreaseMonkey script exports that to your
local storage (this has security implications, but they're not too bad--basically it
lets the VPN site itself access the DSID, but it already has it in a cookie so
that's not horrible; obviously you want proper user permissions on that user storage
database if your machine is a multi-user machine, or even if it has a running ssh
server)

# Future enhancements

* Ask users which sessions to close if any.  Should be relatively simple to do.

* Poll the process output as well as the keyboard so output from openconnect is
  immediately shown.  Or alternatively use CTRL-C to shut down instead of
  any key, but I like to let CTRL-C do a "hard" shutdown to be honest (sometimes
  the process hangs and I'm not sure why)
  
* Allow running as non-root user
  
# Warnings

Please use your own judgement before using this, as some companies don't like such
unofficial VPN clients.  That said, openconnect's code is open, whereas Juniper's
client is a SUID binary which is totally proprietary.  Make your own decisions
accordingly.

It runs as root which can cause problems; that said, it doesn't do any I/O except 
GET/POST to the Juniper server.  Still, if there's some vulnerability in MechanicalSoup
or something I overlooked and you ping a malicious server, it could have dire
consequences.
  
# License

This code is very small, thus I'm placing it in the public domain.  It comes with no
warranty of any kind, and I'm not responsible if it misroutes your packets, doesn't
set up your VPN properly, or gets you in trouble with your corporate IT department
for use of an unofficial VPN client.

This means you can modify it, copy it, and you don't even need to credit me.  I'd still
appreciate that modifications be made through github's forking system so I can see
further work done on this (and possibly use it for myself!), but you have no legal
requirement to do so.
