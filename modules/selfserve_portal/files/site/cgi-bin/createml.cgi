#!/usr/bin/env python
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import os
import sys
import time
import cgi
import requests
import base64
import subprocess
import re
import uuid
import sscommon

requser = os.environ['REMOTE_USER']

def checkDomain(dom):
    """Check if an apache.org ML domain exists or not"""
    rv = requests.get("https://whimsy.apache.org/public/committee-info.json")
    domains = rv.json()['committees']
    
    rv = requests.get("https://whimsy.apache.org/public/public_podlings.json")
    domains.update(rv.json()['podling'])
    
    dlist = ['apache.org']
    for cmt in domains:
        info = domains[cmt]
        if not 'mail_list' in info or not ('@' in info['mail_list'] or ' ' in info['mail_list']):
            dlist.append("%s.apache.org" % (info['mail_list'] if 'mail_list' in info else cmt))
    
    if not dom in dlist:
        return False
    return True

    
    
form = cgi.FieldStorage();

# Get and validate domain part
domain = form.getvalue('domain', None)
if not domain or not checkDomain(domain):
    sscommon.buggo("Invalid domain name!")

# Get and validate list part
listname = form.getvalue('list', None)
if not listname or not re.match(r"^[-a-z]+$", listname):
    sscommon.buggo("Invalid list name specified!")

# Get and validate mods
mods = form.getvalue('moderators', "").split("\n")
for mod in mods:
    if not re.match(r"^\S+@\S+$", mod):
        sscommon.buggo("Invalid administrator username!")

# Get and validate private option
private = form.getvalue("private", False)
if private and listname not in ['private', 'security']:
    sscommon.buggo("Only private@ and security@ can be private by default!")

muopts = form.getvalue('muopts', 'mu')
if not muopts in ['mu', 'Mu', 'mU']:
    sscommon.buggo("Invalid moderation setting requested!")

# Write payload to file
payload = {
    'type': 'mailinglist',
    'requester': requser,
    'requested': int(time.time()),
    'domain': domain,
    'list': listname,
    'muopts': muopts,
    'private': True if private else False,
    'mods': mods
}

uid = uuid.uuid4()
with (open("/usr/local/etc/selfserve/queue/%s-%s-%s.json" % (uid, listname, domain), "w")) as f:
    json.dump(payload, f)
    f.close()


add = "This list has been marked as private. " if private else ""
sscommon.email("%s@apache.org" % requser, "New mailing list queued for creation: %s@%s" % (listname, domain),
"""
Hi there,
As requested by %s@apache.org, a new mailing list have been queued for creation:
%s@%s

%s
This request will automatically be processed within 24 hours.
""" % (requser, listname, domain, add))
sscommon.hipchat("A new mailing list, <kbd>%s@%s</kbd>, has been queued for creation, as requested by %s@apache.org. %s" % (listname, domain, requser, add))
print("Status: 201 Created\r\n\r\n<h2>Mailing List request received!</h2>Your request for a new mailing list has been received and will automatically be processed within 24 hours. We will notify your PMC when the list has been created.")
