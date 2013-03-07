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

# Got a lot of inspiration from cbpscraper.py by Floor Terra

import urllib2
from bs4 import BeautifulSoup
from bs4 import NavigableString
from pprint import pprint
import xlrd
import mechanize
import sys
import time

SEARCH_FORM = "http://register.octrooicentrum.nl/register/zoekformulier"

def get_text(tag):
    s = ""

    for c in tag.contents:
        if isinstance(c, NavigableString):
            s += c
        else:
            s += get_text(c)

    return s

def get_el_class(element, klass):
    return get_text(element.find("div", {"class": klass})).strip()

def get_i1(element):
    return get_el_class(element, "i1")

def get_i2(element):
    return get_el_class(element, "i2")

def get_i3(element):
    return get_el_class(element, "i3")

def get_i4(element):
    return get_el_class(element, "i4")

# Parse an horizontal block with 2 divs.
def parse_hblock2(store, element, cname = None):
    if cname:
        name = cname
    else:
        name = get_i1(element)

    value = get_i2(element)

    store.setdefault(name, [])
    store[name].append(value)

# Parse an horizontal block with 4 divs.
def parse_hblock4(store, element):
    name = get_i1(element)
    value = get_i2(element)

    if name in store:
        raise Exception("field: %s already exists" % ( name, ))

    store[name] = value

    name = get_i3(element)
    value = get_i4(element)

    if name in store:
        raise Exception("field: %s already exists" % ( name, ))

    store[name] = value

def parse_basisgegevens(octrooi, contents):
    basisgegevens = contents.find("div", {"id": "sectie-basisgegevens", })

    octrooi.setdefault('basisgegevens', {})

    for element in basisgegevens.contents:
        if type(element) == NavigableString:
            continue

        if element['class'][0] == 'block-3a':
            # XXX: needs to be written.
            # block-3a is special
            pass

        if get_i1(element) != "":
            cname = get_i1(element)
            
        if element['class'][0] == 'block-4a':
            parse_hblock4(octrooi['basisgegevens'], element)

        if element['class'][0] == 'block-2a':
            parse_hblock2(octrooi['basisgegevens'], element, cname)

def get_element(i):
    element = i.next()
    if type(element) == NavigableString:
        return get_element(i)

    return element
        
def parse_familievoorrang(octrooi, contents):
    familievoorrang = contents.find("div", {"id": "sectie-familieVoorrang", })

    if familievoorrang == None:
        return

    octrooi.setdefault('familievoorrang', [])

    i = iter(familievoorrang.contents)

    try:
        while True:
            element = get_element(i)

            if element['class'][0] == 'block-1a':
                pass
            if element['class'][0] == 'block-4a':
                item = {}
                parse_hblock4(item, element);

                element = get_element(i)

                parse_hblock4(item, element);
                octrooi['familievoorrang'].append(item)
    except StopIteration:
        pass

def parse_sectie_ipc(octrooi, contents):
    sectie_ipc = contents.find("div", {"id": "sectie-ipc", })

    if sectie_ipc == None:
        return

    octrooi.setdefault('sectie_ipc', {})

    for element in sectie_ipc:
        if type(element) == NavigableString:
            continue
        if element['class'][0] == 'block-2a':
            parse_hblock2(octrooi['sectie_ipc'], element)

def parse_sectie_gemachtigdeDomicilie(octrooi, contents):
    domicilie = contents.find("div", {"id": "sectie-gemachtigdeDomicilie", })

    if domicilie == None:
        return

    gemachtigden = []
    cgemachtigde = None
    for element in domicilie:
        if type(element) == NavigableString:
            continue
        if get_i2(element) == "Buitenlandse Gemachtigde" or get_i2(element) == "Voorlopige Domiciliehouder":
            gemachtigde = {'Adres': [], 'van': get_i3(element), 'tot': get_i4(element), 'soort': get_i2(element) }
            gemachtigden.append(gemachtigde)
            cgemachtigde = gemachtigde
            continue

        if get_i1(element) == "Naam":
            cgemachtigde['Naam'] = get_i2(element)
        if get_i1(element) == "Adres":
            cgemachtigde['Adres'].append(get_i2(element))
        if get_i1(element) == "":
            cgemachtigde['Adres'].append(get_i2(element))

    octrooi['gemachtigden'] = gemachtigden


def parse_aanvrager_houder(octrooi, contents):
    aanvrager_houder = contents.find("div", {"id": "sectie-aanvragerHouder", })

    octrooi.setdefault('aanvraaghouder', {})

    clabel = ""
    parsing_address = False
    for element in aanvrager_houder:
        # XXX: Moet van/tot nog parsen
        if type(element) == NavigableString:
            continue
        if get_i2(element) == "Aanvrager/Houder":
            clabel = "aanvrager"
            address_line = 0
        if get_i2(element) == "Historische Aanvrager/Houder":
            clabel = "historische_aanvrager"
            address_line = 0
        if get_i2(element) == "Uitvinder(s)":
            clabel = "uitvinder"
            address_line = 0

        if get_i1(element) == "Adres":
            address_line = 1
        if get_i1(element) == "Naam":
            address_line = 0
            name = get_i2(element)
            octrooi['aanvraaghouder'].setdefault(clabel, {})
            octrooi['aanvraaghouder'][clabel].setdefault('name', [])
            octrooi['aanvraaghouder'][clabel]['name'].append(name)

        if address_line == 1:
            street = get_i2(element)
            address_line = 2
            octrooi['aanvraaghouder'].setdefault(clabel, {})
            octrooi['aanvraaghouder'][clabel]['street'] = street
            continue
        if address_line == 2:
            postal = get_i2(element)
            octrooi['aanvraaghouder'][clabel]['postal'] = postal
            address_line = 3
            continue
        if address_line == 3:
            country = get_i2(element)
            octrooi['aanvraaghouder'][clabel]['country'] = country
            address_line = 0
            continue

def parse_page(octrooi, data):
    b = BeautifulSoup(data)

    contents = b.find("div", {"id": "contents", })

    parse_basisgegevens(octrooi, contents)
    parse_familievoorrang(octrooi, contents)
    parse_sectie_ipc(octrooi, contents)
    parse_aanvrager_houder(octrooi, contents)
    parse_sectie_gemachtigdeDomicilie(octrooi, contents)

def get_patent(patent_number, ipc_klasse):
    br = mechanize.Browser()
    # Fuck robots.txt. Yes, we're fuckin' rebels.
    br.set_handle_robots(False)

    # Today, we will be a linux system running firefox.
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

    resp = br.open(SEARCH_FORM)

    br.select_form("searchForm")

    br["qc_nummer"] = "%d" % ( patent_number, )
    br["qc_ipcklasse"] = ipc_klasse

    resp = br.submit()
    data = resp.read()

    print br.geturl()

    if data.find("Er zijn 0 resultaten gevonden.") > -1:
        print "No results"
        return False

    if data.find("Ter voorkoming van het benaderen van deze site door geautomatiseerde 'robots' vragen wij u de tekst in onderstaande afbeelding over te nemen in de tekstbox.") > -1:
        print "Robot check"
        return False

    return data

def print_usage():
    sys.exit("Usage: %s file" % (sys.argv[0], ))

if __name__ == "__main__":
#    if (len(sys.argv) <= 1):
#        print_usage()
#        # NOTREACHED
#
#    excel_file = sys.argv[1]
#
#    wb = xlrd.open_workbook(excel_file)
#    sh = wb.sheet_by_index(0)
#
#    limit = sh.nrows
#    limit = 90
#    for rownum in range(1, limit):
#        time.sleep(2)
#        number = int(sh.row_values(rownum)[1])
#        ipc_klasse = sh.row_values(rownum)[4]
#
#        octrooi = {}
#
#        print "Retrieving patent: %d" % (number, )
#        data = get_patent(number, ipc_klasse)
#        if (data == False):
#            sys.exit("Couldn't retrieve octrooi number: %d" %( number, ))
#
#        parse_page(octrooi, data)
#
#        pprint(octrooi)

    octrooi = {}

    url = 'http://register.octrooicentrum.nl/register/gegevens/EPNL/90914108E'
    url = 'http://register.octrooicentrum.nl/register/gegevens/EPNL/89306425E'
    data = urllib2.urlopen(url).read()
    parse_page(octrooi, data)
    pprint(octrooi)


