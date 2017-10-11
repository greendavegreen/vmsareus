import json
from time import sleep

from django.http import HttpResponse

import requests
from django.conf import settings


FEATURE_BRANCHES_URL = 'http://stash.lebanon.cd-adapco.com/rest/api/1.0/projects/%s/repos/%s/branches/?limit=1000&filterText=feature&orderBy=MODIFICATION&start=%s'
EXACT_BRANCH_URL = 'http://stash.lebanon.cd-adapco.com/rest/api/1.0/projects/%s/repos/%s/branches/?limit=1000&filterText=%s&orderBy=MODIFICATION&start=%s'


def branch_exists(project, repo, branch_name):
    user = settings.STASH_USER
    pwd = settings.STASH_PW

    url = EXACT_BRANCH_URL % (project, repo, branch_name, 0)
    count = 0
    nl = []

    while True:
        response = requests.get(url, auth=(user, pwd))
        if response.status_code == 200:
            data = response.json()
            for item in data['values']:
                if item['displayId'] == branch_name:
                    return True
            if data['isLastPage']:
                break
            url = FEATURE_BRANCHES_URL % (project, repo, data['nextPageStart'])
            # sleep(1)
        else:
            break
    return False


def get_feature_branches_matching(project, repo, pattern):
    user = settings.STASH_USER
    pwd = settings.STASH_PW

    url = FEATURE_BRANCHES_URL % (project, repo, 0)
    count = 0
    nl = []

    while True:
        response = requests.get(url, auth=(user, pwd))
        if response.status_code == 200:
            data = response.json()
            for item in data['values']:
                if item['displayId'].find(pattern) != -1:
                    nl.append(item['displayId'])
            if data['isLastPage']:
                break
            url = FEATURE_BRANCHES_URL % (project, repo, data['nextPageStart'])
            # sleep(1)
        else:
            break

    return nl


def star_branch_exists(branch_name):
    return branch_exists('dev', 'star', branch_name)


def list_branches(request):
    if request.is_ajax():
        q = request.GET.get('term', '')
        branch_names = get_feature_branches_matching("dev", "star", q)
        results = []
        for bn in branch_names:
            cn_json = {'id': bn,
                       'label': bn,
                       'value': bn}
            results.append(cn_json)
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)
