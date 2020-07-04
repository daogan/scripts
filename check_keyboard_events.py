#!/usr/bin/python

""" A script to log daily key stroke statistics.

Sample output:

Date               	Key Frequency
2020-05-14 23:19:53	{"total": 1310, "cmd": 271, "tab": 210, "enter": 80, "space": 74, ...}
2020-05-15 22:59:04	{"total": 778, "esc": 163, "cmd": 103, "space": 80, "w": 44, ...}
Total              	{"total": 2088, "cmd": 374, "tab": 231, "esc": 163, "space": 154, ...}
"""

import time
import json
from collections import OrderedDict, Counter
from pynput import keyboard


LOG_FILE = '/Users/me/work/misc/keyboard.log'
INTERVAL = 10
INTERVAL_FLUSH = 600

keymap = {}

def on_press(key):
    try:
        kchar = key.char
    except AttributeError:
        kchar = '{0}'.format(key).split('.')[1]
    if kchar is None:
        kchar = '{0}'.format(key)
    keymap.setdefault(kchar, 0)
    keymap[kchar] += 1
    keymap.setdefault('total', 0)
    keymap['total'] += 1

def on_release(key):
    pass

def tts(ts, fmt='%Y-%m-%d %H:%M:%S'):
    return time.strftime(fmt, time.localtime(ts))

def dict_sub(d1, d2):
    return {key: d1[key] - d2.get(key, 0) for key in d1}

def dict_add(d1, d2):
    return dict(Counter(d1) + Counter(d2))

def dict_gt(d1, d2):
    for k in d2:
        if k not in d1 or d1[k] < d2[k]:
            return False
    return True

def run_loop():
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    _fmt = lambda s, n: '{: <{:d}}'.format(s, n)

    with open(LOG_FILE, 'r+') as f:
        lines = f.readlines()
        if not lines or len(lines) < 2:
            f.seek(0)
            f.write('%s\tKey Frequency\n' % _fmt('Date', 19))
            f.write('%s\t{}\n%s\t{}\n' % (tts(time.time()), _fmt('Total', 19)))
            f.truncate()

    last_checked = time.time()
    while True:
        time.sleep(INTERVAL)

        now = time.time()
        if ((now < last_checked + INTERVAL_FLUSH)
                and (tts(now)[:10] == tts(now-INTERVAL)[:10])):
            continue

        last_checked = now

        with open(LOG_FILE, 'r+') as f:
            lines = f.readlines()

        last_date, mlast = lines[-2].split('\t')
        _, mtotal = lines[-1].split('\t')
        mlast = json.loads(mlast)
        mtotal = json.loads(mtotal)
        global keymap
        if dict_gt(keymap, mlast):
            delta_day = dict_sub(keymap, mlast)
        else: # may be a reboot
            delta_day = keymap
            keymap = dict_add(keymap, mlast)
        mtotal = dict_add(mtotal, delta_day)

        okeymap =  OrderedDict(sorted(keymap.iteritems(), key=lambda x: x[1], reverse=True))
        mlast = json.dumps(okeymap)
        ototal =  OrderedDict(sorted(mtotal.iteritems(), key=lambda x: x[1], reverse=True))
        mtotal = json.dumps(ototal)

        now_date = tts(now)
        if last_date[:10] == now_date[:10]:
            lines[-2] = '%s\t%s\n' % (now_date, mlast)
            lines[-1] = '%s\t%s\n' % (_fmt('Total', 19), mtotal)
        else: # cross day
            lines[-2] = '%s\t%s\n' % (last_date, mlast)
            lines[-1] = '%s\t{}\n' % now_date
            lines.append('%s\t%s\n' % (_fmt('Total', 19), mtotal))
            # reset keymap at begining of new day
            keymap= {}

        with open(LOG_FILE, 'r+') as f:
            f.seek(0)
            for line in lines:
                f.write(line)
            f.truncate()

if __name__ == '__main__':
    run_loop()
