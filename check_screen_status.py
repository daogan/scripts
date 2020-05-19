#!/usr/bin/python

""" A script to log the daily screen time on a Macbook.

Track how much time the user spend on a computer everyday.

Sample output:

Date               	Screen time	Power-on time
2020-04-10 23:59:20	08:29:40	22:40:50
2020-04-11 17:15:30	03:04:00	13:36:20
"""

import re
import time
import logging
import subprocess


LOG_FILE = '/Users/me/work/misc/screentime.log'
POWER_MGMT_RE = re.compile(r'IOPowerManagement.*{(.*)}')
INTERVAL = 10
INTERVAL_FLUSH = 600


def display_status():
    output = subprocess.check_output(
        'ioreg -w 0 -c IODisplayWrangler -r IODisplayWrangler'.split())
    status = POWER_MGMT_RE.search(output).group(1)
    return dict((k[1:-1], v) for (k, v) in (x.split('=') for x in
                                            status.split(',')))


def secs_to_hms(n):
    h, r = divmod(n, 3600)
    m, s = divmod(r, 60)
    return '{:02d}:{:02d}:{:02d}'.format(h, m, s)


def hms_to_secs(hms):
    h, m, s = map(int, hms.split(':'))
    return h*3600 + m*60 + s


def tts(ts, fmt='%Y-%m-%d %H:%M:%S'):
    return time.strftime(fmt, time.localtime(ts))


def to_midnight(ts, timezone=time.timezone, use_dst=True):
    """
    Convert a UNIX timestamp to midnight timestamp in local time.

    ts: UNIX timestamp
    timezone: Number of seconds west (behind) to UTC time
    use_dst: Use local DST timezone
    """
    SECS_PER_DAY = 86400
    lt = time.localtime(ts)
    if use_dst and lt.tm_isdst:
        ts += 3600

    secs_since_midnight = ts % SECS_PER_DAY - timezone
    midnight_ts = ts - secs_since_midnight

    if secs_since_midnight > SECS_PER_DAY:
        midnight_ts += SECS_PER_DAY
    elif secs_since_midnight < 0:
        midnight_ts -= SECS_PER_DAY

    if use_dst and lt.tm_isdst and lt.tm_mon > 9:
        midnight_ts -= 3600

    return int(midnight_ts)


def run_loop():

    with open(LOG_FILE, 'r+') as f:
        lines = f.readlines()
        if not lines or len(lines) < 2:
            f.seek(0)
            f.write('%s\tScreen time\tPower-on time\n' % '{: <19}'.format('Date'))
            f.write('%s\t00:00:00\t00:00:00\n' % tts(time.time()))

    screen_time = 0
    power_time = 0
    last_checked = time.time()

    while True:
        time.sleep(INTERVAL)
        power_time += INTERVAL

        status = display_status()
        if status['DevicePowerState'] in ('4', '3'):
            screen_time += INTERVAL

        now = time.time()
        if ((screen_time > 0 and now >= last_checked + INTERVAL_FLUSH)
                or to_midnight(now) != to_midnight(now - INTERVAL)):
            last_checked = now

            with open(LOG_FILE, 'r+') as f:
                lines = f.readlines()
                segs = lines[-1].split('\t')
                last_date, hms, power_hms = segs

                prev_time = hms_to_secs(hms)
                hms = secs_to_hms(prev_time + screen_time)
                power_hms = secs_to_hms(hms_to_secs(power_hms) + power_time)
                screen_time = 0
                power_time = 0

                now_date = tts(now)
                if last_date[:10] == now_date[:10]:
                    lines[-1] = '%s\t%s\t%s\n' % (now_date, hms, power_hms)
                else:
                    lines[-1] = '%s\t%s\t%s\n' % (last_date, hms, power_hms)
                    lines.append('%s\t00:00:00\t00:00:00\n' % now_date)

                f.seek(0)
                for line in lines:
                    f.write(line)
                f.truncate()


if __name__ == '__main__':
    run_loop()
