#!/usr/bin/env python3
#from __future__ import print_function;
import getpass
import subprocess
import os
import sys
import bs4
import urllib
import argparse
from http.client import HTTPConnection

import mechanicalsoup
import bs4.builder

import logging

# Change those as you wish
DEFAULT_VPN_ROUTES = ['10.0.0.0/8']
DEFAULT_IFACE = 'eth0'
DEFAULT_VPN_IFACE = 'tun0'
DEFAULT_PASSWORD2_METHOD = 'push'

# Fix a problem in the "already logged in" form, there's an extra comma after an
# attribute value that breaks beautiful soup.  Not sure whether this is specific
# to our site's version.
class MyTreeBuilder(bs4.builder.HTMLParserTreeBuilder):
    def __init__(self):
        super(MyTreeBuilder, self).__init__()

    def feed(self, markup):
        markup = markup.replace('onclick="checkSelected()",', 'onclick="checkSelected()"')
        return super(MyTreeBuilder, self).feed(markup)

    
def get_dsid(cookies):
    return cookies.get('DSID', None)


p = argparse.ArgumentParser(description='Automate connection to Juniper VPN, with support for DUO')
p.add_argument('server', help='Address of VPN server (without http prefix)')
p.add_argument('--username', help='Your username if you want to pass it directly')
p.add_argument('--secondary', default='push',
               choices=['push', 'phone', 'pin'],
               help='Secondary password, if any.  Push=Duo Push, phone=Callback, pin=PIN from device, you will be prompted.  Note that I never got PIN support to work...')
p.add_argument('--routes', action='append', default=DEFAULT_VPN_ROUTES,
               help='Routes to set.  Defaults to ' + ', '.join(DEFAULT_VPN_ROUTES))
p.add_argument('--no-routes', action='store_const', const=True,
               help='If specified, do not set any routes after connecting')
p.add_argument('--main-iface', help='Main network interface, defaults to ' + DEFAULT_IFACE,
               default=DEFAULT_IFACE)
p.add_argument('--vpn-iface', help='VPN network interface, defaults to ' + DEFAULT_VPN_IFACE,
               default=DEFAULT_VPN_IFACE)
p.add_argument('--debug', action='store_const', const=True,
               help='Trace HTTP traffic.  WARNING: your password will be shown on stdout.')

args = p.parse_args()

username = args.username if args.username else input('Please input your username: ')
password = getpass.getpass('Please input your password: ')
if args.secondary == 'pin':
    secondary = getpass.getpass('Please input your PIN: ')
else:
    secondary = args.secondary

dsid = None

logging.basicConfig()
logger = logging.getLogger("requests.package.urllib3")
logger.propagate = True
if args.debug:
    HTTPConnection.debuglevel = 1
    logger.setLevel(logging.DEBUG)

b = mechanicalsoup.Browser(soup_config=dict(builder=MyTreeBuilder()))

login_page = b.get(''.join(['https://', args.server]))
login_form = login_page.soup.find('form', dict(name='frmLogin'))
login_form.find('input', dict(name='username'))['value'] = username
login_form.find('input', dict(name='password'))['value'] = password
c = login_form.find('input', dict(name='password#2'))
if c is not None:
    c['value'] = args.secondary
if args.secondary == 'push':
    print('Pushing to DUO, please authenticate')
elif args.secondary == 'call':
    print('Calling from DUO, please pick up and answer')

login_response = b.submit(login_form, login_page.url)
if 'p=failed' in login_response.url:
    print('Login failed, please try again')
    sys.exit(1)

dsid = get_dsid(b.session.cookies)

if not dsid:
    # probably a form asking for closing sessions
    close_form = login_response.soup.find('form', dict(name='frmConfirmation'))
    if close_form is None:
        print('Unknown form after login, the script will not work, sorry!')
        print('Please modify the script accordingly')
        sys.exit(2)
    
    c = close_form.find_all('input', dict(type='checkbox', name='postfixSID'))

    vals = []
    for cb in c:
        vals.append(cb['value'])
    url = urllib.parse.urljoin(login_response.url, close_form['action'])
    # unfortunately FormDataStr is *outside* the form according to bs4,
    # so we have to extract it manually
    # we could be more robust by finding all hidden form fields though
    login_response = b.post(url,
                            data=dict(postfixSID=vals,
                                      btnContinue=close_form.find('input',
                                                                  dict(type='submit',
                                                                       name='btnContinue'))['value'],
                                      FormDataStr=login_response.soup.find('input', dict(name='FormDataStr'))['value']),
                            cookies=b.session.cookies,
                            allow_redirects=False)

dsid = get_dsid(b.session.cookies)
if not dsid:
    print("Unable to find DSID, aborting")
    sys.exit(1)

p = subprocess.Popen(['openconnect', '--juniper', '-C', 'DSID='+dsid, args.server],
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    signout = False
    for line in iter(p.stdout.readline, ''):
        line = line.decode('utf-8')
        print(line, end='')
        if line.startswith('ESP session established'):
            # set the routes
            if not args.no_routes:
                subprocess.call(['ip', 'route', 'del', 'default'])
                subprocess.call(['ip', 'route', 'add', 'default', 'via', '192.168.1.1', 'dev', args.main_iface])
                for r in args.routes:
                    subprocess.call(['ip', 'route', 'add', r, 'scope', 'link', 'dev', args.vpn_iface])

            print('Press enter to exit')
            input()
            signout = True
            break
        elif line.startswith('Creating SSL connection failed'):
            print('Failed; abort')
            break
    # force signout
    if signout:
        # hit the signout URL
        # don't handle redirects because for some reason it doesn't
        # work -- possibly because routing table gets reset
        b.get(''.join(['https://', args.server, '/dana-na/auth/logout.cgi']),
              allow_redirects=False,
              cookies=b.session.cookies)
except BaseException as e:
    print(e)
finally:
    try:
        p.poll()
        if p.returncode is None:
            print(p.communicate(timeout=3)[0].decode('utf-8'))
    except BaseException as e:
        print(e)
    try:
        if p.returncode is None:            
            p.poll()
        if p.returncode is None:
            p.wait()
    except BaseException as e:
        print(e)    
