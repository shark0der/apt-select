#!/usr/bin/env python

from sys import exit
from socket import (socket, AF_INET, SOCK_STREAM,
                    gethostbyname, setdefaulttimeout)
from time import time
from re import search
try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

try:
    from bs4 import BeautifulSoup
except ImportError as err:
    print(("%s\n"
           "Try 'sudo apt-get install python-bs4' "
           "or 'sudo apt-get install python3-bs4'" % err))
    exit(1)

class RoundTrip:
    def __init__(self, url):
        self.url = url

    def __tcpPing(self):
        """Return latency to hostname"""
        port = 80
        setdefaulttimeout(2.5)
        s = socket(AF_INET, SOCK_STREAM)
        try:
            addr = gethostbyname(self.url)
        except IOError as err:
            print("Could not resolve hostname\n%s" % err)
            return

        send_tstamp = time()*1000
        try:
            s.connect((addr, port))
        except IOError as err:
            print(err)
            return

        recv_tstamp = time()*1000
        rtt = recv_tstamp - send_tstamp
        s.close()
        return rtt

    def avgRTT(self):
        """Return average rtt"""
        rtt = []
        for i in range(3):
            x = self.__tcpPing()
            if x:
                rtt.append(x)
            else:
                rtt = None
                break

        if rtt:
            avg = round(sum(rtt) / len(rtt))
            return avg
        else:
            return

class Data:
    def __init__(self, url, codename, hardware):
        self.url = url
        self.codename = codename
        self.hardware = hardware
        self.regex = (
            (r'Version\nArchitecture\nStatus\n[\w|\s]'
             '+The\s%s\s\w+\n%s\n(.*)\n' % (self.codename, self.hardware)),
             r'Speed:\n([0-9]{1,3}\s\w+)'
        )

    def __reFind(self, regex, string):
        """Find and return regex match"""
        match = search(regex, string)
        try:
            match = match.group(1)
        except AttributeError:
            pass

        return match

    def getInfo(self):
        """Return mirror status and bandwidth"""
        archive = "https://launchpad.net/ubuntu/+mirror/%s-archive" % self.url
        try:
            launch_html = urlopen(archive)
        except HTTPError:
            try:
                launch_html = urlopen(archive.replace('-archive', ''))
            except HTTPError:
                print(("%s is one of the top mirrors, but "
                       "has a unique launchpad url.\n"
                       "Cannot verify, so removed from list" % self.url))
                return

        launch_html = launch_html.read().decode()
        text = BeautifulSoup(launch_html).get_text()
        status = self.__reFind(self.regex[0], text)
        if not status or 'unknown' in status:
            return

        speed = self.__reFind(self.regex[1], text)
        if not speed:
            return
        else:
            return (self.url, (status, speed))

