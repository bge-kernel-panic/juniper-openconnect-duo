#!/usr/bin/env python3
import getpass
import subprocess
import os
import sys
import bs4
import urllib
import argparse
from pprint import pprint
from http.client import HTTPConnection
import mechanicalsoup
import bs4.builder

import logging

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


p = argparse.ArgumentParser(description='Automate connection to Juniper VPN, with support for FortiNet')
p.add_argument('server', help='Address of VPN server (without http prefix)')
p.add_argument('--username', help='Your username if you want to pass it directly')
p.add_argument('--pwfile', help='Read user password from file')
p.add_argument('--token', help='Manual FortiNet token input', action='store_const', const=True)
p.add_argument('--debug', action='store_const', const=True,
               help='Trace HTTP traffic.  WARNING: your password will be shown on stdout.')

args = p.parse_args()


username = args.username if args.username else input('WebMD Username: ')

if args.pwfile:
    pwfile_fh = open (args.pwfile, "r")
    password = pwfile_fh.read().rstrip ()
    pwfile_fh.close ()
else:
    password = getpass.getpass ('WebMD Password: ')

fortinet_token = 'push' if not args.token else input ('FortiNet PIN: ')
    
dsid = None

logging.basicConfig()
logger = logging.getLogger("requests.package.urllib3")
logger.propagate = True
if args.debug:
    HTTPConnection.debuglevel = 1
    logger.setLevel(logging.DEBUG)

b = mechanicalsoup.StatefulBrowser()
b.open ('https://' + args.server)
b.select_form ()
b['username']=username
b['password']=password
response = b.submit_selected()

if 'p=failed' in response.url:
    print('Login failed, please try again')
    sys.exit(1)

b.select_form ()
b['password']=fortinet_token

if fortinet_token == 'push':
    print('Pushing to FortiNet, please authenticate')

response = b.submit_selected()

dsid = get_dsid(b.session.cookies)

if not dsid:
    # probably a form asking for closing sessions
    close_form = b.select_form ('form[name=frmConfirmation]')
    if close_form is None:
        print('Unknown form after login, the script will not work, sorry!')
        print('Please modify the script accordingly')
        sys.exit(2)
    
    print (close_form.content)
    c = close_form.find_all('input', dict(type='checkbox', name='postfixSID'))

    vals = []
    for cb in c:
        vals.append(cb['value'])
    url = urllib.parse.urljoin(fortinet_page.url, close_form['action'])
    # unfortunately FormDataStr is *outside* the form according to bs4,
    # so we have to extract it manually
    # we could be more robust by finding all hidden form fields though
    fortinet_page = b.post(url,
                            data=dict(postfixSID=vals,
                                      btnContinue=close_form.find('input',
                                                                  dict(type='submit',
                                                                       name='btnContinue'))['value'],
                                      FormDataStr=fortinet_page.soup.find('input', dict(name='FormDataStr'))['value']),
                            cookies=b.session.cookies,
                            allow_redirects=False)

dsid = get_dsid(b.session.cookies)
if not dsid:
    print("Unable to find DSID, aborting")
    sys.exit(1)
oc_args = ['openconnect', '--juniper', '-C', 'DSID='+dsid]
if args.debug:
    oc_args.append('--dump-http-traffic')
oc_args.append(args.server)
p = subprocess.Popen(oc_args,
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
signout = False
try:
    for line in iter(p.stdout.readline, ''):
        line = line.decode('utf-8')
        print(line, end='')
        if line.startswith('Connected as') and line.rstrip().endswith(', using SSL'):
            print('Press CTRL-C to exit')
            signout = True
        elif line.startswith('ESP session established'):
            print('Press enter to exit')
            input()
            signout = True
            break
        elif line.startswith('Creating SSL connection failed'):
            print('Failed; abort')
            break
except BaseException as e:
    print('Exception, aborting.')
    if args.debug:
        print(e)
finally:
    # force signout
    if signout:
        print('Disconnect.')
        # hit the signout URL
        # don't handle redirects because for some reason it doesn't
        # work -- possibly because routing table gets reset
        b.get(''.join(['https://', args.server, '/dana-na/auth/logout.cgi']),
              allow_redirects=False,
              cookies=b.session.cookies)
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
