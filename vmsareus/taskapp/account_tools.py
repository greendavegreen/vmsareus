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


def create_client(addr, user, password):
    client = SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy)
    client.connect(addr, 22, user, password)
    return client


def do_cmd(client, command, verbose=True):
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
            print ("copied %s to %s" % (srcName, dstName))
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
        do_cmd(ssh, 'mkdir /home/davidgr/.ssh')
    finally:
        ssh.close()


def set_ssh_perms(address,user,pw):
    try:
        ssh = create_client(address, user, pw)
        do_cmd(ssh, 'chmod 400 /home/davidgr/.ssh/id_rsa')
        do_cmd(ssh, 'chmod 744 /home/davidgr/.ssh/id_rsa.pub')
        do_cmd(ssh, 'chmod 700 /home/davidgr/.ssh')
    finally:
        ssh.close()


STASH_SSH_KEY_URL = 'http://stash.lebanon.cd-adapco.com/rest/ssh/1.0/keys'


def add_key_to_user(target_user, key_data):
    user = settings.STASH_USER
    pwd = settings.STASH_PW
    url = STASH_SSH_KEY_URL

    payload = {'text': key_data}
    headers = {'X-Atlassian-Token': 'nocheck',
               'Accept': 'application/json',
               'Content-Type': 'application/json'}
    r = requests.post(url, data=json.dumps(payload), headers=headers, auth=(user, pwd))

    if r.status_code == 201:
        print("successfully added key")
        new_key_id = r.json()['id']
        return new_key_id
    else:
        print("error posting key %s" % r.status_code)
        return None


def setup_ssh_for_user(address, user, pw, id_input):
    make_ssh_dir(address, user, pw)

    keypair = make_keys()
    copy_bytes_to_target(address, user, pw,
                         keypair['private'],
                         '/home/davidgr/.ssh/id_rsa')
    copy_bytes_to_target(address, user, pw,
                         keypair['public'],
                         '/home/davidgr/.ssh/id_rsa.pub')

    set_ssh_perms(address, user, pw)

    machine_id = 'vm_%s@vmsareus' % id_input
    new_id = add_key_to_user(user, keypair['public'] + ' ' + machine_id)
    if new_id:
        print('new ssh key id = %s' % new_id)


def add_user_to_windows_machine(address, user):
    client = None
    try:
        newpw = gen_dev_password()
        client = create_client(address, user=settings.VM_DEFUSER, password=settings.VM_DEFPW)
        do_cmd(client, "net user %s %s /add /Y" % (user, newpw), verbose=False)
        do_cmd(client, "net localgroup administrators %s /add" % (user))
        do_cmd(client, "mkdir /home/%s" % (user))
    except:
        print("exception during add_user_to_windows_machine")
        return None
    else:
        return newpw
    finally:
        if client:
            client.close()
