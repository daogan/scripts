#!/usr/bin/python

""" A script to log the daily and monthly network traffic on a computer.

Sample output:

               Date	 Rx_Mon_GiB	Tx_Mon_GiB	Rx_Day_GiB	Tx_Day_GiB
2020-04-10 23:59:09	     261.81	    145.99	     11.24	      3.85
2020-04-11 17:25:32	     268.82	    156.71	      7.01	     10.71
"""

from __future__ import division
import re
import sys
import time
import subprocess


INTERFACE = 'en0'
LOG_FILE = '/Users/me/work/misc/daily_traffic.log'
INTERVAL = 10
INTERVAL_FLUSH = 600
GiB = 1024**3
RE_IP = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}')


def get_network_bytes_linux(interface):
    output = subprocess.Popen(['ifconfig', interface],
                              stdout=subprocess.PIPE).communicate()[0]
    rx_bytes = re.findall('RX bytes:([0-9]*) ', output)[0]
    tx_bytes = re.findall('TX bytes:([0-9]*) ', output)[0]
    return (rx_bytes, tx_bytes)


def get_network_bytes_macos(interface):
    rx_bytes, tx_bytes = 0, 0
    lines = subprocess.check_output(
        ['/usr/sbin/netstat','-ib', '-I', interface]
    ).strip().split('\n')
    for line in lines:
        segs = line.split()
        if len(segs) > 9 and RE_IP.match(segs[2]):
            rx_bytes, tx_bytes = segs[6], segs[9]
            break
    return (rx_bytes, tx_bytes)


def tts(ts, fmt='%Y-%m-%d %H:%M:%S'):
    return time.strftime(fmt, time.localtime(ts))


def run_loop():
    if sys.platform == 'darwin':
        get_network_bytes = get_network_bytes_macos
    elif sys.platform.startswith('linux'):
        get_network_bytes = get_network_bytes_linux
    else:
        return

    _fmt = lambda s, n: '{: >{:d}}'.format(s, n)
    headers = [
        _fmt('Date', 19),
        _fmt('Rx_Bytes', 12), _fmt('Tx_Bytes', 12),
        _fmt('Rx_Month', 12), _fmt('Tx_Month', 12),
        _fmt('Rx_Day', 11), _fmt('Tx_Day', 11),
        'Rx_Mon_GiB', 'Tx_Mon_GiB',
        'Rx_Day_GiB', 'Tx_Day_GiB'
    ]

    def _fmt_line(words):
        ws = []
        for idx, word in enumerate(words):
            ws.append('{: >{:d}}'.format(word, len(headers[idx])))
        return '%s\n' % '\t'.join(ws)

    with open(LOG_FILE, 'r+') as f:
        lines = f.readlines()
        if not lines or len(lines) < 2:
            rx, tx = get_network_bytes(INTERFACE)
            l = [tts(time.time()), rx, tx] + [0] * 8
            f.seek(0)
            f.write(_fmt_line(headers))
            f.write(_fmt_line(l))

    last_checked = time.time()
    while True:
        time.sleep(INTERVAL)

        now = time.time()
        if ((now < last_checked + INTERVAL_FLUSH)
                and (tts(now)[:10] == tts(now-INTERVAL)[:10])):
            continue

        last_checked = now

        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()

        segs = lines[-1].split('\t')
        last_date = segs[0]
        rx0, tx0, mrx, mtx, drx, dtx = map(int, segs[1:7])
        rx1, tx1 = map(int, get_network_bytes(INTERFACE))

        if not (rx1 > 0 and tx1 > 0):
            continue

        delta_rx = max(rx1 - rx0, 0)
        delta_tx = max(tx1 - tx0, 0)
        mrx += delta_rx
        mtx += delta_tx
        drx += delta_rx
        dtx += delta_tx

        now_date = tts(now)
        cross_day = True if last_date[:10] != now_date[:10] else False
        cross_mon = True if last_date[:7] != now_date[:7] else False
        last_date = last_date if cross_day else now_date

        gibs = map(lambda x: '{:.2f}'.format(x / GiB), [mrx, mtx, drx, dtx])
        lines[-1] = _fmt_line([last_date, rx1, tx1, mrx, mtx, drx, dtx] + gibs)

        if cross_mon:
            mrx, mtx = 0, 0
        if cross_day:
            lines.append(_fmt_line([now_date, rx1, tx1, mrx, mtx, 0, 0] + gibs))

        try:
            with open(LOG_FILE, 'r+') as f:
                f.seek(0)
                for line in lines:
                    f.write(line)
                f.truncate()
        except:
            return


if __name__ == '__main__':
    run_loop()
