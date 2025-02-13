import unittest.mock

import pytest

from middlewared.utils.disks import get_disk_names, VALID_WHOLE_DISK


@pytest.mark.parametrize('to_test, should_work', [
    ('sda', True),
    ('sdab', True),
    ('sdz', True),
    ('vdv', True),
    ('vds', True),
    ('nvme0n0', True),
    ('nvme2n4', True),
    ('vda1', False),
    ('vdA', False),
    ('sd2', False),
    ('sda2', False),
    ('sda3', False),
    ('vda3', False),
])
def test_regex(to_test, should_work):
    if should_work:
        assert bool(VALID_WHOLE_DISK.match(to_test)) is True
    else:
        assert bool(VALID_WHOLE_DISK.match(to_test)) is False


@unittest.mock.patch('os.scandir')
def test_get_disk_names(scandir):
    mock_devices = []
    for name in ['vda', 'vdb', 'sda', 'sdd', 'nvme0n1', 'sdd1', 'sda2', 'vdb2']:
        device = unittest.mock.Mock(is_file=lambda: True)
        device.name = name  # Set the name attribute directly
        mock_devices.append(device)

    scandir.return_value.__enter__.return_value = mock_devices
    assert get_disk_names() is not None
    assert get_disk_names() == ['vda', 'vdb', 'sda', 'sdd', 'nvme0n1']
