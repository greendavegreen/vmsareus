from django.conf import settings
from xml.dom.minidom import parseString
from django.contrib.auth.backends import ModelBackend


import requests

from vmsareus.users.models import User

class JiraBackend(ModelBackend):
    """
    This is the Attlasian (JIRA) Authentication Backend for Django
    Have a nice day! Hope you will never need opening this file looking for a bug =)
    """

    def authenticate(self, username, password):
        """
        Main authentication method
        """
        jira_url = self._get_jira_config()
        if not jira_url:
            return None
        user = self._find_existing_user(username)
        response = self._call_jira(username, password, jira_url)
        if response.status_code == 200:
            if user:
                user.set_password(password)
            else:
                self._create_new_user_from_jira_response(username, password, response.content, jira_url)
            return user
        else:
            return None

    def _get_jira_config(self):
        """
        Returns CROWD-related project settings. Private service method.
        """
        config = getattr(settings, 'JIRA_URL', None)
        if not config:
            raise UserWarning('Jira configuration is not set in your settings.py, while authorization backend is set')
        return config

    def _find_existing_user(self, username):
        """
        Finds an existing user with provided username if one exists. Private service method.
        """
        users = User.objects.filter(username=username)
        if users.count() <= 0:
            return None
        else:
            return users[0]

    def _call_jira(self, username, password, jira_url):
        """
        Calls Jira user directory service via REST API
        """
        url = jira_url + "/auth/latest/session"
        body = '{"username" : "%s", "password" : "%s"}' % (username, password)

        return requests.post(url, headers={'content-type': 'application/json'}, data=body)

    def _create_new_user_from_jira_response(self, username, password, content, jira_url):
        """
        Creating a new user in django auth database basing on information provided by CROWD. Private service method.
        """
        user_data = self._get_user_data(username, password, jira_url)
        if not user_data:
            email = "user@example.com"
        else:
            email = user_data['emailAddress']

        user = User.objects.create_user(username, email, password)
        user.is_active = True
        # auto-superuser goodness goes here once I figure things out
        # if 'superuser' in crowd_config and crowd_config['superuser']:
        #user.is_superuser = True
        #user.is_staff = True
        if user_data:
            user.name = user_data['displayName']

        #     user.is_staff = user.is_superuser
        user.save()
        return user

    def _get_user_data(self, username, password, jira_url):
        url = jira_url + "/api/latest/user?username=%s&expand=groups" % username
        r = requests.get(url, auth=(username, password))
        if not r.status_code == 200:
            return None
        return r.json()
