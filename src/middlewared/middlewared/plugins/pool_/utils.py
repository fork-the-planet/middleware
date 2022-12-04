ZFS_CHECKSUM_CHOICES = ['ON', 'OFF', 'FLETCHER2', 'FLETCHER4', 'SHA256', 'SHA512', 'SKEIN', 'EDONR']
ZFS_ENCRYPTION_ALGORITHM_CHOICES = [
    'AES-128-CCM', 'AES-192-CCM', 'AES-256-CCM', 'AES-128-GCM', 'AES-192-GCM', 'AES-256-GCM'
]
ZPOOL_CACHE_FILE = '/data/zfs/zpool.cache'
ZPOOL_KILLCACHE = '/data/zfs/killcache'


def _null(x):
    if x == 'none':
        return None
    return x


def get_props_of_interest_mapping():
    return [
        ('org.freenas:description', 'comments', None),
        ('org.freenas:quota_warning', 'quota_warning', None),
        ('org.freenas:quota_critical', 'quota_critical', None),
        ('org.freenas:refquota_warning', 'refquota_warning', None),
        ('org.freenas:refquota_critical', 'refquota_critical', None),
        ('org.truenas:managedby', 'managedby', None),
        ('dedup', 'deduplication', str.upper),
        ('mountpoint', None, _null),
        ('aclmode', None, str.upper),
        ('acltype', None, str.upper),
        ('xattr', None, str.upper),
        ('atime', None, str.upper),
        ('casesensitivity', None, str.upper),
        ('checksum', None, str.upper),
        ('exec', None, str.upper),
        ('sync', None, str.upper),
        ('compression', None, str.upper),
        ('compressratio', None, None),
        ('origin', None, None),
        ('quota', None, _null),
        ('refquota', None, _null),
        ('reservation', None, _null),
        ('refreservation', None, _null),
        ('copies', None, None),
        ('snapdir', None, str.upper),
        ('readonly', None, str.upper),
        ('recordsize', None, None),
        ('sparse', None, None),
        ('volsize', None, None),
        ('volblocksize', None, None),
        ('keyformat', 'key_format', lambda o: o.upper() if o != 'none' else None),
        ('encryption', 'encryption_algorithm', lambda o: o.upper() if o != 'off' else None),
        ('used', None, None),
        ('usedbychildren', None, None),
        ('usedbydataset', None, None),
        ('usedbyrefreservation', None, None),
        ('usedbysnapshots', None, None),
        ('available', None, None),
        ('special_small_blocks', 'special_small_block_size', None),
        ('pbkdf2iters', None, None),
        ('creation', None, None),
        ('snapdev', None, str.upper),
    ]