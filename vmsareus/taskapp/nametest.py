import unittest

from ..taskapp.vmware_tools import make_travelling_drive_url, make_dev_vm_drive_url


# offer some examples of calls to the URL generator and the type of output they will produce

class TravellingDriveTest(unittest.TestCase):
    def test_exact_branch(self):
        self.assertEqual(make_travelling_drive_url('https://vcenter.lebanon.cd-adapco.com',
                                                   'gitworkflow-workspaces',
                                                   'davidgr_VRU_100',
                                                   'windows',
                                                   'Lebanon',
                                                   'san3-travelingDrives1'),
                         "https://vcenter.lebanon.cd-adapco.com/folder/gitworkflow-workspaces/davidgr_VRU_100_windows.vmdk?dcPath=Lebanon&dsName=san3-travelingDrives1")

    def test_full_feature_name(self):
        self.assertEqual(make_travelling_drive_url('https://vcenter.lebanon.cd-adapco.com',
                                                   'gitworkflow-workspaces',
                                                   'feature/davidgr/VRU-100',
                                                   'windows',
                                                   'Lebanon',
                                                   'san3-travelingDrives1'),
                         "https://vcenter.lebanon.cd-adapco.com/folder/gitworkflow-workspaces/davidgr_VRU_100_windows.vmdk?dcPath=Lebanon&dsName=san3-travelingDrives1")


    def test_dot_in_branch_name(self):
        self.assertEqual(make_travelling_drive_url('https://vcenter.lebanon.cd-adapco.com',
                                                   'gitworkflow-workspaces',
                                                   'feature/davidgr/VRU-100.nothing',
                                                   'windows',
                                                   'Lebanon',
                                                   'san3-travelingDrives1'),
                         "https://vcenter.lebanon.cd-adapco.com/folder/gitworkflow-workspaces/davidgr_VRU_100.nothing_windows.vmdk?dcPath=Lebanon&dsName=san3-travelingDrives1")


class DevDriveTest(unittest.TestCase):
    def test_exact_branch(self):
        self.assertEqual(make_dev_vm_drive_url('https://vcenter.lebanon.cd-adapco.com',
                                               'gitworkflow-workspaces',
                                               'davidgr_fluff/VRU.100',
                                               'windows',
                                               10,
                                               'Lebanon',
                                               'san3-travelingDrives1'),
                         "https://vcenter.lebanon.cd-adapco.com/folder/gitworkflow-workspaces/davidgr_fluff_VRU.100_windows_dev10.vmdk?dcPath=Lebanon&dsName=san3-travelingDrives1")


if __name__ == '__main__':
    unittest.main()
