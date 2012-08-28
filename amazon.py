import logging
import time
import re
import string
import sys

from google.appengine.api import urlfetch
from google.appengine.ext import db

from photobook import *

class Amazon():
    MODULE = "amazon"

    URL = "http://www.amazon.com"
    URL_BOOK = URL + "/amazon/dp/"
    URL_TIMEOUT = 30

    TITLE_PARSER = (r"meta name=\"title\" content=\"Amazon.com: (?P<title>.*)\([0-9]+\):", 'title', 0)
    AUTHOR_PARSER = (r"meta name=\"title\" content=.*\([0-9]+\):(?P<author>.*):", 'author', 0)
    BOUND_PARSER = (r"<li><b>(?P<bound>.*):</b>.*pages</li>", 'bound', 0)
    LANGUAGE_PARSER = (r"Language:</b>(?P<language>.*)</li>", 'language', 0)
    ISBN13_PARSER = (r"ISBN-13:</b>(?P<isbn13>.*)</li>", 'isbn13', 0)
    PAGE_PARSER = (r":</b>(?P<page>.*)pages</li>", 'page', 0)
    WEIGHT_PARSER = (r"Weight:</b>(?P<weight>.*)(pounds|ounces)", 'weight', 0)
    DIMENSION_PARSER = (r"Dimensions:.*?</b>(?P<dimension>.*?)inches.*?</li>", 'dimension', re.DOTALL)
    PUBLISHER_PARSER = (r"Publisher:</b> (?P<publisher>.*)[(]", 'publisher', 0)
    #COVER_PARSER = (r"(?P<cover>(ecx|_cache).*?[.]jpg)", 'cover', 0)
    PRICE_PARSER = (r"listprice\">(?P<price>\$[0-9]+[.][0-9][0-9])", 'price', 0)
    DESC_PARSER = (r"div id=\"postBodyPS\">(?P<desc>.*?)</div>", 'desc', re.DOTALL)
    #ISBN_PARSER = (r"ISBN (?P<isbn>[0-9]+)", 'isbn', 0)
    YEAR_PARSER = (r"Publication Date:.*(?P<year>[0-9][0-9][0-9][0-9])", 'year', 0)

    def get_book(self, id):
        logging.info("Get Book: {}".format(id))
        if id == '':
            return "Invalid ID"

        book = {}
        result = urlfetch.fetch(self.URL_BOOK + id, deadline=self.URL_TIMEOUT)
        if result.status_code != 200:
            return None

        buf = result.content
        book['uid'] = self.MODULE + '.' + id
        book['source_url'] = self.URL_BOOK + id

        titles = self._extract(self.TITLE_PARSER, buf).split(':', 1)
        book['title'] = titles[0].strip()
        if len(titles) > 1: 
            book['sub_title'] = titles[1].strip()
        book['author'] = self._extract(self.AUTHOR_PARSER, buf)
        if book['author']:
            book['author'] = book['author'].decode('utf-8').split(', ')

        book['desc'] = self._extract(self.DESC_PARSER, buf)
        book['extent'] = self._extract(self.BOUND_PARSER, buf)
        book['language'] = self._extract(self.LANGUAGE_PARSER, buf)
        dimension = self._extract(self.DIMENSION_PARSER, buf)
        if dimension:
            dl = dimension.split('x')
            book['width'] = self._calc_size(dl[0])
            book['height'] = self._calc_size(dl[1])
            book['thickness'] = self._calc_size(dl[2])
            if book['thickness'] > book['height']:
                book['thickness'], book['height'] = book['height'], book['thickness']

        book['page'] = self._extract(self.PAGE_PARSER, buf)
        book['weight'] = self._calc_weight(self._extract(self.WEIGHT_PARSER, buf))
        book['isbn13'] = self._extract(self.ISBN13_PARSER, buf).replace('-', '')
        book['price'] = self._extract(self.PRICE_PARSER, buf)
        book['year'] = self._extract(self.YEAR_PARSER, buf)
        book['publisher'] = self._extract(self.PUBLISHER_PARSER, buf)
        if book['publisher']:
            book['publisher'] = string.replace(book['publisher'], 'Publishers', '').strip()
        return book

    def _extract(self, parser, str):
        c = re.compile(parser[0], parser[2])
        m = c.search(str)
        if m:
            return m.group(parser[1]).strip()
        return None

    def _calc_size(self, str):
        if not str:
            return 0
        result = float(str) * 25.4
        return int(result)

    def _calc_weight(self, str):
        if not str:
            return float(0)

        result = float(str) * 453.59237 / 1000.0
        return result

amazon = Amazon()

