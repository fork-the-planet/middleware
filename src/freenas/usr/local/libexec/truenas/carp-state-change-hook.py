#!/usr/bin/env python
from lockfile import LockFile

import atexit
import json
import logging
import logging.config
import os
import subprocess
import sys
import time


ELECTING_FILE = '/tmp/.failover_electing'
IMPORTING_FILE = '/tmp/.failover_importing'
FAILED_FILE = '/tmp/.failover_failed'
FAILOVER_ASSUMED_MASTER = '/tmp/.failover_master'
FAILOVER_FORCE_SEAL = '/tmp/force_seal'
FAILOVER_JSON = '/tmp/failover.json'
FAILOVER_MTX = '/tmp/.failover_mtx'
FAILOVER_OVERRIDE = '/tmp/failover_override'
FAILOVER_STATE = '/tmp/.failover_state'
FAILOVER_NEEDOP = '/tmp/.failover_needop'
HEARTBEAT_BARRIER = '/tmp/heartbeat_barrier'
HEARTBEAT_STATE = '/tmp/heartbeat_state'

log = logging.getLogger('carp-state-change-hook')


def run(cmd):
    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        shell=True,
    )
    output = proc.communicate()[0]
    return (proc.returncode, output.strip('\n'))


def main(ifname, event):

    if ifname in ('carp1', 'carp2'):
        sys.exit(1)

    if not os.path.exists(FAILOVER_JSON):
        sys.exit(1)

    state_file = '%s%s' % (FAILOVER_STATE, event)

    @atexit.register
    def cleanup():
        try:
            os.unlink(state_file)
        except:
            pass

    with LockFile(FAILOVER_MTX):
        if not os.path.exists(state_file):
            open(state_file, 'w').close()
        else:
            sys.exit(0)

    with open(FAILOVER_JSON, 'r') as f:
        fobj = json.loads(f.read())

    SENTINEL = False
    for group in fobj['groups']:
        for interface in fobj['groups'][group]:
            if ifname == interface:
                SENTINEL = True

    if not SENTINEL:
        log.warn("Ignoring state change on non-critical interface %s.", ifname)
        sys.exit()

    if fobj['disabled']:
        if not fobj['master']:
            log.warn("Failover disabled.  Assuming backup.")
            sys.exit()
        else:
            masterret = False
            for vol in fobj['volumes']:
                ret = os.system("zpool status %s" % vol)
                if ret:
                    masterret = True
                    for group in fobj['groups']:
                        for interface in fobj['groups'][group]:
                            run("ifconfig %s advskew 0" % interface)
                    log.warn("Failover disabled.  Assuming active.")
                    run("touch %s" % FAILOVER_OVERRIDE)
            if masterret is False:
                sys.exit()

    open(HEARTBEAT_BARRIER, 'a+').close()

    now = int(time.time())
    os.utime(HEARTBEAT_BARRIER, (now, now))

    user_override = True if os.path.exists(FAILOVER_OVERRIDE) else False
    forceseal = True if (
        os.path.exists(FAILOVER_FORCE_SEAL) and
        os.stat(FAILOVER_FORCE_SEAL).st_mtime > now
    ) else False

    if event == 'LINK_UP':
        link_up(fobj, state_file, ifname, event, forceseal, user_override)
    elif event == 'LINK_DOWN':
        link_down(fobj, state_file, ifname, event, forceseal, user_override)


def link_up(fobj, state_file, ifname, event, forceseal, user_override):

    log.warn("Entering UP on %s", ifname)

    if not forceseal and not user_override:
        sleeper = fobj['timeout']
        error, output = run("ifconfig lagg0")
        if not error:
            if sleeper < 2:
                sleeper = 2
            log.warn("Sleeping %s seconds and rechecking %s", sleeper, ifname)
            # FIXME
            time.sleep(sleeper)
            error, output = run(
                "ifconfig %s | grep 'carp:' | awk '{print $2}'" % ifname
            )
            if output != 'MASTER':
                log.warn("%s became %s. Previous event ignored.", ifname, output)
                sys.exit(0)
        else:
            log.warn("Sleeping %s seconds and rechecking %s", sleeper, ifname)
            time.sleep(sleeper)
            error, output = run(
                "ifconfig %s | grep 'carp:' | awk '{print $2}'" % ifname
            )
            if output != 'MASTER':
                log.warn("%s became %s. Previous event ignored.", ifname, output)
                sys.exit(0)

    if os.path.exists(FAILOVER_ASSUMED_MASTER):
        error, output = run("ifconfig -l")
        for iface in output.split():
            print iface
            if iface.startswith("carp") and (iface != "carp1" and iface != "carp2"):
                run("ifconfig %s advskew 1" % iface)
        sys.exit(0)

    totoutput = 0
    for group, carpint in fobj['groups'].items():
        for i in carpint:
            error, output = run("ifconfig %s | grep 'carp: BACKUP' | wc -l" % i)
            totoutput += int(output)

            if not error and totoutput > 0:
                log.warn(
                    'Ignoring UP state on %s because we still have interfaces that are'
                    ' BACKUP.', ifname
                )
                run('echo "$(date), $(hostname), %s assumed master while other '
                    'interfaces are still in slave mode." | mail -s "Failover WARNING"'
                    ' root' % ifname)
                sys.exit(1)

    run('pkill -f fenced')

    with open('/etc/pf.conf.block', 'w+') as f:
        f.write('set block-policy drop\n')
        for ip in fobj['ips']:
            f.write('''
pass in quick proto tcp from any to %(ip)s  port {22, 80, 443}
block drop in quick proto tcp from any to %(ip)s
block drop in quick proto udp from any to %(ip)s''' % {'ip': ip})
    run('pfctl -f /etc/pf.conf.block')

    try:
        os.unlink(FAILED_FILE)
    except:
        pass
    try:
        os.unlink(IMPORTING_FILE)
    except:
        pass
    open(ELECTING_FILE, 'w').close()

    was_connected = True if (
        os.path.exists(HEARTBEAT_STATE) and
        os.stat(HEARTBEAT_STATE).st_mtime > os.stat(HEARTBEAT_BARRIER).st_mtime
    ) else False
    fasttrack = False

    if was_connected:
        time.sleep(1)
        error, status0 = run(
            "ifconfig %s | grep 'carp:' | awk '{print $2}'" % ifname
        )
        error, status1 = run(
            "(ifconfig carp1 | grep carp: | awk '{print $2;}' ; ifconfig carp2"
            "| grep carp: | awk '{print $2;}')|grep -E '(MASTER|INIT)' | wc -l"
        )
        error, status2 = run(
            "(ifconfig carp1 | grep carp: | awk '{print $2;}' ; ifconfig carp2"
            "| grep carp: | awk '{print $2;}')|grep BACKUP | wc -l"
        )

        log.warn('Status: %s:%s:%s', status0, status1, status2)

        if status0 != 'MASTER':
            log.warn('Promoted then demoted, quitting.')
            # Just in case.  Demote ourselves.
            run('ifconfig %s advskew 202' % ifname)
            try:
                os.unlink(ELECTING_FILE)
            except:
                pass
            sys.exit(0)

        if int(status1) == 2 and int(status2) == 0:
            fasttrack = True

    if forceseal:
        fasttrack = True

    log.warn('Starting fenced')
    run('/sbin/camcontrol rescan all')
    if not user_override and not fasttrack:
        error, output = run('LD_LIBRARY_PATH=/usr/local/lib /usr/local/bin/python /usr/local/sbin/fenced')
    else:
        error, output = run(
            'LD_LIBRARY_PATH=/usr/local/lib /usr/local/bin/python /usr/local/sbin/fenced force'
        )

    if error:
        if error == 1:
            log.warn('Can not register keys on disks!')
            run('ifconfig %s advskew 201' % ifname)
        elif error == 2:
            log.warn('Remote fenced is running!')
            run('ifconfig %s advskew 202' % ifname)
        elif error == 3:
            log.warn('Can not reserve all disks!')
            run('ifconfig %s advskew 203' % ifname)
        elif error == 5:
            log.warn('Fencing daemon encountered an unexpected fatal error!')
            run('ifconfig %s advskew 205' % ifname)
        else:
            log.warn('This should never happen: %d', error)
            run('ifconfig %s advskew 204' % ifname)
        try:
            os.unlink(ELECTING_FILE)
        except:
            pass
        sys.exit(1)

    # If we reached here, fenced is daemonized and have all drives reserved.
    # Bring up all carps we own.
    error, output = run("ifconfig -l")
    for iface in output.split():
        print iface
        if iface.startswith("carp") and (iface != "carp1" and iface != "carp2"):
            run("ifconfig %s advskew 1" % iface)

    open(IMPORTING_FILE, 'w').close()
    try:
        os.unlink(ELECTING_FILE)
    except:
        pass

    run("sysctl -n kern.disks | tr ' ' '\\n' | sed -e 's,^,/dev/,' | grep '^/dev/da' | xargs -n 1 echo 'false >' | sh")

    if os.path.exists('/data/zfs/killcache'):
        run('rm -f /data/zfs/zpool.cache /data/zfs/zpool.cache.saved')
    else:
        open('/data/zfs/killcache', 'w').close()
        run('fsync /data/zfs/killcache')

    if os.path.exists('/data/zfs/zpool.cache'):
        stat1 = os.stat('/data/zfs/zpool.cache')
        if (
            not os.path.exists('/data/zfs/zpool.cache.saved') or
            stat1.st_mtime > os.stat('/data/zfs/zpool.cache.saved').st_mtime
        ):
            run('cp /data/zfs/zpool.cache /data/zfs/zpool.cache.saved')

    log.warn('Beginning volume imports.')
    # TODO: now that we are all python, we should probably just absorb the code in.
    run(
        '/usr/local/bin/python /usr/local/www/freenasUI/failover/enc_helper.py'
        ' attachall'
    )

    for volume in fobj['volumes']:
        log.warn('Importing %s', volume)
        error, output = run('/sbin/zpool import %s -o cachefile=none -R /mnt -f %s' % (
            '-c /data/zfs/zpool.cache.saved' if os.path.exists(
                '-c /data/zfs/zpool.cache.saved'
            ) else '',
            volume,
        ))
        if error:
            open(FAILED_FILE, 'w').close()
        run('/sbin/zpool set cachefile=/data/zfs/zpool.cache %s' % volume)

    if not os.path.exists(FAILOVER_NEEDOP):
        open(FAILOVER_ASSUMED_MASTER, 'w').close()

    try:
        os.unlink('/data/zfs/killcache')
    except:
        pass

    if not os.path.exists(FAILED_FILE):
        run('cp /data/zfs/zpool.cache /data/zfs/zpool.cache.saved')
    try:
        os.unlink(IMPORTING_FILE)
    except:
        pass

    log.warn('Volume imports complete.')
    log.warn('Restarting services.')

    run('/usr/local/bin/python /usr/local/www/freenasUI/middleware/notifier.py'
        ' nfsv4link')
    run('/usr/sbin/service /etc/rc.d/statd quietstart')
    run('/usr/sbin/service ix-nfsd quietstart')
    run('/usr/sbin/service mountd quietrestart')
    run('/usr/sbin/service nfsd quietrestart')
    run('/usr/sbin/service ix-ctld quietstart')
    run('/usr/sbin/service ctld forcestop')
    run('/usr/sbin/service ctld quietstart')
    run('/usr/sbin/service ix-system quietstart')
    run('/usr/sbin/service ix-samba quietstart')
    run('/usr/sbin/service samba_server forcestop')
    run('/usr/sbin/service samba_server quietstart')
    run('/usr/sbin/service ix-afpd quietstart')
    run('/usr/sbin/service netatalk forcestop')
    run('/usr/sbin/service netatalk quietstart')

    log.warn('Service restarts complete.')

    # There appears to be a small lag if we allow NFS traffic right away. During
    # this time, we fail NFS requests with ESTALE to the remote system. This
    # gives remote clients heartburn, so rather than try to deal with the
    # downstream effect of that, instead we take a chill pill for 2 seconds.
    time.sleep(1)

    with open('/etc/pf.conf', 'w+') as f:
        for ip in fobj['ips']:
            f.write('pass quick from any to %s keep state\n' % ip)
    run('pfctl -f /etc/pf.conf')

    log.warn('Allowing network traffic.')
    run('echo "$(date), $(hostname), assume master" | mail -s "Failover" root')

    try:
        os.unlink(FAILOVER_OVERRIDE)
    except:
        pass

    run('/usr/sbin/service ix-crontab quietstart')

    log.warn('Syncing enclosure')
    run('/usr/local/bin/python /usr/local/www/freenasUI/middleware/notifier.py'
        ' zpool_enclosure_sync')

    run('/usr/sbin/service ix-collectd quietstart')
    run('/usr/sbin/service collectd quietrestart')
    run('/usr/sbin/service ix-syslogd quietstart')
    run('/usr/sbin/service syslogd quietrestart')

    log.warn('Failover event complete.')


def link_down(fobj, state_file, ifname, event, forceseal, user_override):
    log.warn("Entering DOWN on %s", ifname)

    if not forceseal and not user_override:
        sleeper = fobj['timeout']
        error, output = run("ifconfig lagg0")
        if not error:
            if sleeper < 2:
                sleeper = 2
            log.warn("Sleeping %s seconds and rechecking %s", sleeper, ifname)
            # FIXME
            time.sleep(sleeper)
            error, output = run(
                "ifconfig %s | grep 'carp:' | awk '{print $2}'" % ifname
            )
            if output == 'MASTER':
                log.warn("Ignoring state on %s because it changed back to MASTER after "
                         "%s seconds.",  ifname, sleeper)
                sys.exit(0)
        else:
            log.warn("Sleeping %s seconds and rechecking %s", sleeper, ifname)
            time.sleep(sleeper)
            error, output = run(
                "ifconfig %s | grep 'carp:' | awk '{print $2}'" % ifname
            )
            if output == 'MASTER':
                log.warn("Ignoring state on %s because it changed back to MASTER after "
                     "%s seconds.", ifname, sleeper)
                sys.exit(0)

    totoutput = 0
    for group, carpint in fobj['groups'].items():
        for i in carpint:
            error, output = run("ifconfig %s | grep 'carp: MASTER' | wc -l" % i)
            totoutput += int(output)

            if not error and totoutput > 0:
                log.warn(
                    'Ignoring DOWN state on %s because we still have interfaces that '
                    'are UP.', ifname)
                sys.exit(1)

    run('pkill -f fenced')

    for group in fobj['groups']:
        for interface in fobj['groups'][group]:
            run("ifconfig %s advskew 100" % interface)

    with open('/etc/pf.conf.block', 'w+') as f:
        f.write('set block-policy drop\n')
        for ip in fobj['ips']:
            f.write('''
pass in quick proto tcp from any to %(ip)s port {22, 80, 443}
block drop in quick proto tcp from any to %(ip)s
block drop in quick proto udp from any to %(ip)s''' % {'ip': ip})
    run('pfctl -f /etc/pf.conf.block')

    run('/etc/rc.d/statd stop')
    run('/etc/rc.d/watchdogd quietstop')
    run('watchdog -t 4')

    for volume in fobj['volumes']:
        error, output = run('zpool list %s' % volume)
        if not error:
            log.warn('Exporting %s', volume)
            error, output = run('zpool export -f %s' % volume)
            if error:
                run('zpool status %s' % volume)
                time.sleep(5)
            log.warn('Exported %s', volume)

    run('watchdog -t 0')
    try:
        os.unlink(FAILOVER_ASSUMED_MASTER)
    except:
        pass

    run('/etc/rc.d/watchdogd quietstart')
    run('/usr/sbin/service ix-syslogd quietstart')
    run('/usr/sbin/service syslogd quietrestart')
    run('/usr/sbin/service ix-crontab quietstart')
    run('/usr/sbin/service ix-collectd quietstart')
    run('/usr/sbin/service collectd forcestop')
    run('echo "$(date), $(hostname), assume backup" | mail -s "Failover" root')

    log.warn('Syncing enclosure')
    run('/usr/local/bin/python /usr/local/www/freenasUI/middleware/notifier.py'
        ' zpool_enclosure_sync')
    log.warn('Setting passphrase from master')
    run('/usr/local/bin/python /usr/local/www/freenasUI/failover/enc_helper.py'
        ' syncfrompeer')


if __name__ == '__main__':

    if os.path.exists("/var/run/log"):
        logging.config.dictConfig({
            'version': 1,
            #'disable_existing_loggers': True,
            'formatters': {
                'simple': {
                    'format': '[%(name)s:%(lineno)s] %(message)s',
                },
            },
            'handlers': {
                'syslog': {
                    'class': 'logging.handlers.SysLogHandler',
                    'address': '/var/run/log',
                    'formatter': 'simple',
                    'level': 'DEBUG',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['syslog'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
            },
        })
    else:
        logging.config.dictConfig({
            'version': 1,
            #'disable_existing_loggers': True,
            'formatters': {
                'simple': {
                    'format': '[%(name)s:%(lineno)s] %(message)s',
                },
            },
            'handlers': {
                'console': {
                    'class' : 'logging.StreamHandler',
                    'formatter': 'simple',
                    'level'   : 'INFO',
                    'stream'  : 'ext://sys.stdout',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['console'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
            },
        })
    log = logging.getLogger('carp.state-change-hook')

    main(*sys.argv[1:])
