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

from bs4 import BeautifulSoup
from bs4 import NavigableString
from pprint import pprint
import sys
import os
import json

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

def get_basisgegevens(contents):
    basisgegevens = contents.find("div", {"id": "sectie-basisgegevens", })

    data = {}

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
            parse_hblock4(data, element)

        if element['class'][0] == 'block-2a':
            parse_hblock2(data, element, cname)

    return data

def get_element(i):
    element = i.next()
    if type(element) == NavigableString:
        return get_element(i)

    return element
        
def get_familievoorrang(contents):
    familievoorrang = contents.find("div", {"id": "sectie-familieVoorrang", })

    if familievoorrang == None:
        return

    data = []

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
                data.append(item)
    except StopIteration:
        pass

    return data

def get_sectie_ipc(contents):
    sectie_ipc = contents.find("div", {"id": "sectie-ipc", })

    if sectie_ipc == None:
        return

    data = {}

    for element in sectie_ipc:
        if type(element) == NavigableString:
            continue
        if element['class'][0] == 'block-2a':
            parse_hblock2(data, element)

    return data

def get_gemachtigden(contents):
    domicilie = contents.find("div", {"id": "sectie-gemachtigdeDomicilie", })

    if domicilie == None:
        return

    gemachtigden = []
    cgemachtigde = None
    for element in domicilie:
        if type(element) == NavigableString:
            continue
        known_gemachtigden = [
            "Domiciliehouder",
            "Gemachtigde",
            "Buitenlandse Gemachtigde",
            "Voorlopige Domiciliehouder",
        ]
        if get_i2(element) in known_gemachtigden:
            if element['class'][0] == 'block-2c':
                gemachtigde = {'Adres': [], 'soort': get_i2(element) }
                gemachtigden.append(gemachtigde)
                cgemachtigde = gemachtigde
                continue
            elif element['class'][0] == 'block-4c':
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

    return gemachtigden

def get_aanvrager_houder(contents):
    aanvrager_houder = contents.find("div", {"id": "sectie-aanvragerHouder", })

    data = {}

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
            data.setdefault(clabel, {})
            data[clabel].setdefault('name', [])
            data[clabel]['name'].append(name)

        if address_line == 1:
            street = get_i2(element)
            address_line = 2
            data.setdefault(clabel, {})
            data[clabel]['street'] = street
            continue
        if address_line == 2:
            postal = get_i2(element)
            data[clabel]['postal'] = postal
            address_line = 3
            continue
        if address_line == 3:
            country = get_i2(element)
            data[clabel]['country'] = country
            address_line = 0
            continue

    return data

def get_octrooi(data):
    b = BeautifulSoup(data)

    contents = b.find("div", {"id": "contents", })

    return {
        'gemachtigden': get_gemachtigden(contents),
        'basisgegevens': get_basisgegevens(contents),
        'familie': get_familievoorrang(contents),
        'ipc': get_sectie_ipc(contents),
        'aanvrager_houder': get_aanvrager_houder(contents),
    }

def print_usage():
    sys.exit("Usage: %s dir" % (sys.argv[0], ))

if __name__ == "__main__":
    if (len(sys.argv) <= 1):
        print_usage()
        # NOTREACHED

    octrooi_dir = sys.argv[1]

    for filename in os.listdir(octrooi_dir):
        if not filename.endswith('.json'):
            continue

        filedescr = open(os.path.join(octrooi_dir, filename), 'r')
        file_data = filedescr.read()
        json_data = json.loads(file_data)
        html_data = json_data['data'] 

        if 'error' in json_data:
            print json_data['error']
            continue

        octrooi = get_octrooi(data)
        pprint(octrooi)
