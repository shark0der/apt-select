#!/usr/bin/env python

from sys import exit
from os import getcwd
from re import findall, search
from subprocess import check_output, CalledProcessError
from argparse import ArgumentParser

try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

from mirrors import RoundTrip, Data

parser = ArgumentParser()
parser.add_argument('--auto', '-a', action='store_true', help='auto: choose the best mirror', default=False)
args = parser.parse_args()
flag_auto = args.auto

def notUbuntu():
    print("Not an Ubuntu OS")
    exit(1)

try:
    release = check_output("lsb_release -ics 2>/dev/null", shell=True)
except CalledProcessError:
    notUbuntu()
else:
    release = [s.strip() for s in release.decode().split()]

hardware = check_output("uname -m", shell=True).strip().decode()
if release[0] == 'Debian':
    print("Debian is not currently supported")
    exit(1)
elif release[0] != 'Ubuntu':
    notUbuntu()

codename = release[1][0].upper() + release[1][1:]
mirror_list = "http://mirrors.ubuntu.com/mirrors.txt"
try:
    archives = urlopen(mirror_list)
except IOError as err:
    print(("Could not connect to '%s'.\n"
           "%s" % (mirror_list, err)))
    exit(1)

print("Got list of mirrors")
archives = archives.read().decode()
urls = findall(r'http://([\w|\.|\-]+)/', archives)
n = 0
avg_rtts = {}
for url in urls:
    ping = RoundTrip(url)
    print("Connecting to %s" % url)
    avg = ping.avgRTT()
    if avg:
        avg_rtts.update({url:avg})
        n += 1

print("Tested %d mirrors" % n)
if hardware == 'x86_64':
    hardware = 'amd64'
else:
    hardware = 'i386'

top_num = 5
ranks = sorted(avg_rtts, key=avg_rtts.__getitem__)
info = []
print("Retrieving status information")
for rank in ranks:
    d = Data(rank, codename, hardware)
    data = d.getInfo()
    if data:
        info.append(data)

    if len(info) == top_num:
        break

print("\nTop %d mirrors:\n" % top_num)
for i, j in enumerate(info):
    print("%d. %s\n\tLatency: %d ms\n\tStatus: %s\n\tBandwidth: %s\n" %
          (i + 1, j[0], avg_rtts[j[0]], j[1][0], j[1][1]))

directory = '/etc/apt/'
apt_file = 'sources.list'
try:
    input = raw_input
except NameError:
    pass

def ask(query, default):

    global input, flag_auto

    if flag_auto:
        return default

    answer = input(query)
    return answer

query = "Choose a mirror from the list (1 - %d) " % top_num
key = ask(query, '1')

while True:
    match = search(r'[1-5]', key)
    if match and (len(key) == 1):
        key = int(key)
        break
    else:
        query = "Please enter a valid number "
        key = ask(query)

key = key - 1
mirror = info[key][0]
for m in archives.splitlines():
    if mirror in m:
        mirror = m
        break

found = None
field1 = ('deb', 'deb-src')
h = 'http://'
with open('%s' % directory + apt_file, 'r') as f:
    lines = f.readlines()
    for line in lines:
        arr = line.split()
        if not found:
            if (arr and (arr[0] in field1) and
                    (h == arr[1][:7]) and
                    (release[1] in arr[2:])):
                repo = [arr[1]]
                found = True
                continue
        else:
            if (arr and (arr[0] in field1) and
                    (h in arr[1]) and
                    (arr[2] == '%s-security' % (release[1]))):
                repo += [arr[1]]
                break

    else:
        print("Error finding current repositories")
        exit(1)

lines = ''.join(lines)
for r in repo:
    lines = lines.replace(r, mirror)

def yesOrNo():
    y = 'yes'
    n = 'no'
    query = ''
    options = "Please enter '%s' or '%s': " % (y,n)
    while True:
        answer = ask(query, 'yes')
        if answer == y:
            break
        elif answer == n:
            exit(0)
        else:
            query = options

wd = getcwd()
if wd == directory[0:-1]:
    query = (
        "'%(dir)s' is the current directory.\n"
        "Generating a new '%(apt)s' file will "
        "overwrite the current file.\n"
        "You should copy or backup '%(apt)s' before replacing it.\n"
        "Continue?\n[yes|no] " %
        {'dir': directory, 'apt': apt_file}
    )
    yesOrNo()

try:
    with open(apt_file, 'w') as f:
        f.write(lines)
except IOError as err:
    if err.strerror == 'Permission denied':
        print(("%s\nYou do not own %s\n"
               "Please run the script from a directory you own." %
               (err, wd)))
        exit(1)

exit(0)
