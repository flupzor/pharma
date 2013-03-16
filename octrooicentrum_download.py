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

import urllib2
import mechanize
import sys
import xlrd
import time
import random
import json

SEARCH_FORM = "http://register.octrooicentrum.nl/register/zoekformulier"

def get_page(patent_number, ipc_klasse):
    br = mechanize.Browser()
    # Fuck robots.txt. Yes, we're fuckin' rebels.
    br.set_handle_robots(False)

    # Today, we will be a linux system running firefox.
    x = random.randint(1, 500);
    y = random.randint(1, 500);
    z = random.randint(1, 500);
    br.addheaders = [
        ('User-agent',
        'Mozilla/%d.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/%d Fedora/%d.0.1-1.fc9 Firefox/3.0.1' % (x, y, z))
    ]

    resp = br.open(SEARCH_FORM)

    br.select_form("searchForm")

    br["qc_nummer"] = "%d" % ( patent_number, )
    br["qc_ipcklasse"] = ipc_klasse

    resp = br.submit()
    data = resp.read()

    if data.find("Er zijn 0 resultaten gevonden.") > -1:
        return { 'url': br.geturl(), 'data': '', 'error': "No results"}

    if data.find("Ter voorkoming van het benaderen van deze site door geautomatiseerde 'robots' vragen wij u de tekst in onderstaande afbeelding over te nemen in de tekstbox.") > -1:
        print "Robot check"
        return False

    return { 'url': br.geturl(), 'data': data }

def print_usage():
    sys.exit("Usage: %s file" % (sys.argv[0], ))

if __name__ == "__main__":
    if (len(sys.argv) <= 1):
        print_usage()
        # NOTREACHED

    excel_file = sys.argv[1]

    wb = xlrd.open_workbook(excel_file)
    sh = wb.sheet_by_index(0)

    limit = sh.nrows
    for rownum in range(1, limit):
        time.sleep(5)
        number = int(sh.row_values(rownum)[1])
        ipc_klasse = sh.row_values(rownum)[4]

        data = get_page(number, ipc_klasse)
        if (data == False):
            sys.exit("Couldn't retrieve octrooi number: %d" %( number, ))

        print "Retrieving patent: %d (%d of %d) url: %s" % (number, rownum, limit, data['url'])

        json_file = open('octrooi_files/%s.json' % (number, ), 'w')
        json_file.write(json.dumps(data))
        json_file.close()

