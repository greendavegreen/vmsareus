import time

import re
from pyVmomi import vim

from vmware_tools import copy_disk, delete_disk, attach_drive, disk_exists

url_template = '{host}/folder/{path}/{branch}_{host_os}.vmdk?dcPath={datacenter}&dsName={datastore}'
file_template = '[{datastore}] {path}/{branch}_{host_os}.vmdk'

dir_url_template = '{host}/folder/{path}?dcPath={datacenter}&dsName={datastore}'
dir_path_template = '[{datastore}] {path}'


def normalize_branch_name(i_branch):
    if i_branch.startswith('feature/'):
        i_branch = i_branch[8:]

    return re.sub('[^0-9a-zA-Z._]+', '_', i_branch)


def make_dev_drive_filename(i_datastore, i_path, i_branch, i_os, i_vm_id):
    clean_branch = normalize_branch_name(i_branch)

    return file_template.format(datastore=i_datastore,
                                path=i_path,
                                branch=clean_branch,
                                host_os=i_os + ('_dev%s' % i_vm_id))


def make_travelling_drive_url(i_host, i_path, i_branch, i_os, i_datacenter, i_datastore):
    clean_branch = normalize_branch_name(i_branch)

    return url_template.format(host=i_host,
                               path=i_path,
                               branch=clean_branch,
                               host_os=i_os,
                               datacenter=i_datacenter,
                               datastore=i_datastore)


def make_dev_vm_drive_url(i_host, i_path, i_branch, i_os, i_vm_id, i_datacenter, i_datastore):
    return make_travelling_drive_url(i_host,
                                     i_path,
                                     i_branch,
                                     i_os + ('_dev%s' % i_vm_id),
                                     i_datacenter,
                                     i_datastore)


def make_target_folder_url(i_host, i_path, i_datacenter, i_datastore):
    return dir_url_template.format(host=i_host,
                               path=i_path,
                               datacenter=i_datacenter,
                               datastore=i_datastore)


def make_dev_drive_for_branch(branch, vm_id):
    host = 'https://vcenter.lebanon.cd-adapco.com'
    host_os = 'windows'
    dc = 'Lebanon'

    path = 'gitworkflow-workspaces'
    ds = 'san3-travelingDrives1'
    src_url = make_travelling_drive_url(host, path, branch, host_os, dc, ds)

    new_path = 'dev-vm-drives'
    new_ds = 'rdx1-vmsareus3'
    dst_url = make_dev_vm_drive_url(host, new_path, branch, host_os, vm_id, dc, new_ds)

    workToDo = True
    start_time = time.time()

    while workToDo:
        try:
            copy_disk(src_url, dst_url)
        except vim.fault.FileLocked:
            # timeout after four hours
            elapsed = time.time() - start_time
            if elapsed > 60 * 60 * 4:
                raise RuntimeError('timeout awaiting travelling drive to become free.')
        else:
            print('copy completed:')
            print(src_url)
            print(dst_url)
            workToDo = False


def td_exists(branch):
    host = 'https://vcenter.lebanon.cd-adapco.com'
    host_os = 'windows'
    dc = 'Lebanon'

    path = 'gitworkflow-workspaces'
    ds = 'san3-travelingDrives1'
    src_url = make_travelling_drive_url(host, path, branch, host_os, dc, ds)

    print(src_url)
    return disk_exists(src_url)


def delete_dev_drive(branch, vm_id):
    host = 'https://vcenter.lebanon.cd-adapco.com'
    host_os = 'windows'
    dc = 'Lebanon'
    new_path = 'dev-vm-drives'
    new_ds = 'rdx1-vmsareus3'

    target_url = make_dev_vm_drive_url(host, new_path, branch, host_os, vm_id, dc, new_ds)
    delete_disk(target_url)


def attach_dev_drive(vm_name, branch, vm_id):
    host_os = 'windows'
    path = 'dev-vm-drives'
    ds = 'rdx1-vmsareus3'

    file_name = make_dev_drive_filename(ds, path,  branch, host_os, vm_id)
    attach_drive(vm_name, file_name)


# def confirm_vm_dir():
#     host = 'https://vcenter.lebanon.cd-adapco.com'
#     path = 'new-dev-vm-drives'
#     dc = 'Lebanon'
#     ds = 'rdx1-vmsareus3'
#
#     url = make_target_folder_url(host, path, dc, ds)
#     make_dir_if_not_present(url)


def test_drive_create():
    make_dev_drive_for_branch('feature/davidgr/VRU-100', 10)


def test_drive_delete():
    delete_dev_drive('feature/davidgr/VRU-100', 23)


def test_attach():
    attach_dev_drive('dev-vm-davidgr-1507228404', 'feature/davidgr/VRU-100', 10)

def test_live_copy():
    branch = 'feature/davidgr/VRU-100'

    host = 'https://vcenter.lebanon.cd-adapco.com'
    host_os = 'windows'
    dc = 'Lebanon'
    new_path = 'dev-vm-drives'
    new_ds = 'rdx1-vmsareus3'

    src_url = make_dev_vm_drive_url(host, new_path, branch, host_os, 46, dc, new_ds)
    dst_url = make_dev_vm_drive_url(host, new_path, branch, host_os, 99, dc, new_ds)

    print(src_url)
    print(dst_url)
    try:
        copy_disk(src_url, dst_url)
    except vim.fault.FileLocked:
        print("file locked")
    else:
        print("file copied")
