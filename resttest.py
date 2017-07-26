import json

import httplib2
import base64
import requests

username = "davidgr"
password = "7s1^YkGP6H*#"
jira_url = "http://jira.cd-adapco.com/rest"
url = jira_url + "/api/latest/user?username=%s" % username

r = requests.get(url, auth=(username, password))
#print (r.status_code)
#print (r.content)
j = r.json()
em = j['emailAddress']
print(em)

# body = '{"username" : "%s", "password" : "%s"}' % (username, password)
# h = httplib2.Http()
# url = jira_url + "/api/latest/user?username=%s" % username
# auth = username + ':' + password
# auth = base64.b64encode(auth.encode())
#
# resp, content = h.request(url, "GET", headers={'Authorization': 'Basic ' + auth})
# print(resp.status)
# print(content)
