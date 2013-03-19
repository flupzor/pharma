#!/usr/bin/env python

# Copyright (c) 2013 Alexander Schrijver <alex@flupzor.nl>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import division
import json
import httplib
import sys
import socket
import ssl
import time
import os
import signal

stop_requested = 0

def int_handler(signum, frame):
    global stop_requested
    stop_requested = 1

class HTTPSConnectionWithLowEncryption(httplib.HTTPSConnection):
    "This class allows communication via SSL with low encryption"

    def connect(self):
        "Connect to a host on a given (SSL) port."

        sock = socket.create_connection((self.host, self.port),
                                        self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ciphers="LOW")

def get_patent(conn, patent_number):
    conn.request("GET", "/espacenet/download?number=%s&tab=main&xml=st36" % (patent_number, ))

    response = conn.getresponse()
    data = response.read()

    return data

def print_usage():
    sys.exit("Usage: %s file" % (sys.argv[0], ))

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print_usage()
        # NOTREACHED

    # Handle process interrupts in the event loop. This way we don't stop the
    # processing while it is writing the json file (or something else).
    signal.signal(signal.SIGINT, int_handler)
    signal.siginterrupt(signal.SIGINT, False)

    json_filename = sys.argv[1]

    file_descr = open(json_filename, 'r')
    patent_numbers = json.loads(file_descr.read())

    conn = HTTPSConnectionWithLowEncryption("register.epo.org")

    start_time = time.time()
    bytes_recv = 0
    session_bytes_recv = 0
    total_expected_bytes = 0
    total_patents_recv = 0
    avg_patent_size = 0
    total_number_of_patents = len(patent_numbers)

    for patent in patent_numbers:
        filename = "%s.xml" % (patent, )
        path = os.path.join("epo_files/", filename)

        running_time = time.time() - start_time

        # Skip files which have been already downloaded
        try:
            patent_descr = open(path, "r")

            patent_size = len(patent_descr.read())

            total_patents_recv += 1
            bytes_recv += patent_size

            patent_descr.close()

            continue
        except IOError:
            pass

        patent_descr = open(path, "w")
        patent_data = get_patent(conn, patent)
        patent_size = len(patent_data)

        total_patents_recv += 1
        session_bytes_recv += patent_size
        bytes_recv += patent_size

        bytes_per_sec = session_bytes_recv / running_time 

        avg_patent_size = bytes_recv / total_patents_recv

        total_expected_bytes = avg_patent_size * total_number_of_patents
        expected_bytes_left = total_expected_bytes - bytes_recv

        print "%f%% size: %d kbps: %d, time remaining in hours: %d" % (bytes_recv /
            total_expected_bytes * 100, patent_size, bytes_per_sec/1024, 1/bytes_per_sec *
            expected_bytes_left / 60**2 )

        patent_descr.write(patent_data)
        patent_descr.close()

        if stop_requested:
            sys.exit("Process interruption requested by the user")

        time.sleep(1) # 1 second


