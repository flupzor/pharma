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

# http://www.epo.org/
# This tool goes through the epo registry using a certain IPC and finds all the
# patentnumbers. The results are written to a file using the JSON format.

import time
import json
import sys
import urllib2
import mechanize
import urlparse
from bs4 import BeautifulSoup
from bs4 import NavigableString

IPC="A61P"
SEARCH_FORM="https://register.epo.org/espacenet/advancedSearch?lng=en"
PAGE="https://register.epo.org/espacenet/advancedSearch?searchMode=advanced&pr=&pn=&prd=&page=%d&ap=&pa=&ic=" + IPC + "&pd=&ti=&recent=1&in=&re=&fd=&op="

def get_lastpagenr(b):
    pagination = b.find("div", {"class": "fullPaginationResults"})
    last = pagination.find("a", {"class": "paginationLast"})
    lastpagenr = int(urlparse.parse_qs(last['href'])['page'][0])

    return lastpagenr

def get_results(b):
    application = b.find("table", {"class": "application"})
    index = application.tbody

    result_list = []

    for i in index:
        if isinstance(i, NavigableString):
            continue
        if i.has_key('class') and ('even' in i['class'] or 'odd' in i['class']):
            continue
        result_list.append(i.th.a['href'].replace('application?number=', ''))

    return result_list

def get_page_n(br, n):
    res = br.open(PAGE % (n,))
    data = res.read()

    return data

if __name__ == "__main__":
    br = mechanize.Browser()
    # Fuck robots.txt. Yes, we're fuckin' rebels.
    br.set_handle_robots(False)

    resp = br.open(SEARCH_FORM)

    br.select_form(nr=0)

    # The form on the page says the enctype is "utf-8". "utf-8" isn't a valid
    # enctype. So we override it with something that is valid.
    br.form.enctype = "application/x-www-form-urlencoded"

    br["ic"] = "A61P"

    resp = br.submit()
    data = resp.read()

    b = BeautifulSoup(data)

    number_of_pages = get_lastpagenr(b)

    result_list = []
    for i in range(1, number_of_pages):
        print "page %d of %d" % (i, number_of_pages)
        data = get_page_n(br, i)
        if data == False:
            sys.exit("Fail")

        b = BeautifulSoup(data)
        result_list += get_results(b)

        time.sleep(1)

    file_descr = open("%s.json" % (IPC,), "w")
    file_descr.write(json.dumps(result_list))

