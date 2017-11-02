import json
import tempfile

import requests
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from paramiko import AutoAddPolicy
from paramiko import SSHClient
from scp import SCPClient

from genpass import gen_dev_password


def make_keys():
    keypair = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )
    private_key = keypair.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption())
    public_key = keypair.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )
    return {'private': private_key, 'public': public_key}


def create_client(address, user, password):
    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy)
    client.connect(address, 22, user, password)
    return client


def do_cmd(client, command, verbose=False):
    if verbose:
        print("running " + command)
    stdin, stdout, stderr = client.exec_command(command)
    stdin.close()
    for line in stdout.read().splitlines():
        if verbose:
            print('remote-output -> %s' % (line))


def copy_file_to_target(address, user, password, srcName, dstName):
    try:
        ssh = create_client(address, user, password)
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(srcName, dstName)
    finally:
        ssh.close()


def copy_bytes_to_target(address, user, password, bytes, dest):
    tmp = tempfile.NamedTemporaryFile(delete=True)
    try:
        tmp.write(bytes)
        tmp.seek(0)
        copy_file_to_target(address, user, password, tmp.name, dest)
    finally:
        tmp.close()  # deletes the file

def make_ssh_dir(address, user, pw):
    try:
        ssh = create_client(address, user, pw)
        do_cmd(ssh, 'mkdir /home/%s/.ssh' % user)
    finally:
        ssh.close()


def customize_git_params(address, user, pw):
    try:
        ssh = create_client(address, user, pw)
        do_cmd(ssh, 'shopt -s dotglob && chown -R %s:None /cygdrive/e/star/*' % user, True)
        do_cmd(ssh, "sed -i '/worktree/d' /cygdrive/e/star/.git/config", True)
        do_cmd(ssh, "cd /cygdrive/e/star && git reset --hard", True)
        do_cmd(ssh, "cd /cygdrive/e/star && git status", True)
    finally:
        ssh.close()


def set_ssh_perms(address,user,pw):
    try:
        ssh = create_client(address, user, pw)
        do_cmd(ssh, 'chmod 400 /home/%s/.ssh/id_rsa' % user)
        do_cmd(ssh, 'chmod 664 /home/%s/.ssh/known_hosts' % user)
        do_cmd(ssh, 'chmod 744 /home/%s/.ssh/id_rsa.pub' % user)
        do_cmd(ssh, 'chmod 700 /home/%s/.ssh' % user)
    finally:
        ssh.close()


STASH_SSH_KEY_URL = 'http://stash.lebanon.cd-adapco.com/rest/ssh/1.0/keys?user=%s'
STASH_SSH_KEY_DELETE_URL = 'http://stash.lebanon.cd-adapco.com/rest/ssh/1.0/keys/%s'


def delete_stash_key(key_id):
    user = settings.STASH_USER
    pwd = settings.STASH_PW
    url = STASH_SSH_KEY_DELETE_URL % key_id

    # headers = {'X-Atlassian-Token': 'nocheck',
    #            'Accept': 'application/json',
    #            'Content-Type': 'application/json'}
    print(url)
    r = requests.delete(url, auth=(user, pwd))

    if r.status_code != 204:
        raise RuntimeError("error posting key %s" % r.status_code)


def add_key_to_user(target_user, key_data):
    user = settings.STASH_USER
    pwd = settings.STASH_PW
    url = STASH_SSH_KEY_URL % target_user

    payload = {'text': key_data}
    headers = {'X-Atlassian-Token': 'nocheck',
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    print (url)
    r = requests.post(url, data=json.dumps(payload), headers=headers, auth=(user, pwd))

    if r.status_code == 201:
        return r.json()['id']
    else:
        raise RuntimeError("error posting key %s" % r.status_code)


def setup_desktop_for_user(address, user, pw):
    targetName = '/cygdrive/c/Users/%s/Desktop/linkDevToE.bat' % user
    tmp = tempfile.NamedTemporaryFile(delete=True)
    try:
        tmp.write("pushd c:\home\%s \r\n" % user)
        tmp.write("mklink /d dev e:\\ \r\n")
        tmp.write("popd \r\n")
        tmp.seek(0)
        copy_file_to_target(address, user, pw, tmp.name, targetName)
    except:
        raise
    else:
        print('copied bat file to %s' % targetName)
    finally:
        tmp.close()  # deletes the file


def setup_ssh_for_user(address, user, pw, id_input):
    try:
        make_ssh_dir(address, user, pw)

        keypair = make_keys()
        copy_bytes_to_target(address, user, pw,
                             keypair['private'],
                             '/home/%s/.ssh/id_rsa' % user)
        copy_bytes_to_target(address, user, pw,
                             keypair['public'],
                             '/home/%s/.ssh/id_rsa.pub' % user)
        stash_signature="stash,192.168.118.140 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDJHrsM9STlBsX5bF0v80Y+NBi276FnG+xTScr0wXP4vr9q+w+ZxIhKtPqLssbEfZAy8OciJGRtsX0hRxoBwDLUdHbHVCsx+fPrRPYUG3fnhIh4ZmRXja/B46bi+oh/fzDLm4QzyTcbd0pyBeAjlZbJ39KpaaSn/YEK1/jl8xPKl0E1GUYrMOUJ2Zs59sWq/m2YWxOVHnl0/u26Xs2wyelSY3ZC3W3Ar7XaMPVccRA5MMbueEFjIoXHrhLGxcJANEFxjewnJYN/Dt+OG00mngXBPHOBE+wauKM5z+bVnAh5gidGHvzd837Sv08BfUx4saibzXMt+xWNJ6LS4QRW2J2h\n"
        copy_bytes_to_target(address, user, pw,
                             stash_signature,
                             '/home/%s/.ssh/known_hosts' % user)
        set_ssh_perms(address, user, pw)

        machine_id = 'vm_%s@vmsareus' % id_input
        new_id = add_key_to_user(user, keypair['public'] + ' ' + machine_id)
    except:
        raise
    else:
        print('new ssh key id = %s' % new_id)
        return new_id


def add_user_to_windows_machine(address, new_user):
    client = None
    try:
        client = create_client(address, user=settings.VM_DEFUSER, password=settings.VM_DEFPW)
        new_pw = gen_dev_password()
        do_cmd(client, "net user %s %s /add /Y" % (new_user, new_pw))
        do_cmd(client, "net localgroup administrators %s /add" % (new_user))
        do_cmd(client, "mkdir /home/%s" % (new_user))
    except:
        print('account add failed for machine %s account %s' % (address, new_user))
        raise
    else:
        print('account added on machine %s account %s' % (address, new_user))
        return new_pw
    finally:
        if client:
            client.close()
