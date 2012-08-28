import logging
import time
import re
import string
import os
import traceback

from google.appengine.api import urlfetch
from google.appengine.api import images
from google.appengine.ext import db
from google.appengine.api import files
from google.appengine.ext.webapp import template

from photobook import *
from amazon import *

class Photoeye():
    MODULE = "photoeye"

    URL = "http://www.photoeye.com"
    URL_NEW_ARRIVALS = URL + "/bookstore/newarrivals.cfm"
    URL_BOOK = URL + "/bookstore/citation.cfm?Catalog="
    URL_TEASE = URL + "/BookteaseLight/bookteaselight.cfm?catalog="
    URL_TIMEOUT = 30

    KEY_PATTERN = r"[A-Z][A-Z][0-9][0-9][0-9]"

    TITLE_PARSER = (r"subject3.+>(?P<title>.*)[.]</", 'title', 0)
    BLOCK_PARSER = (r"<em>(?P<block>.*)</em> </font>", 'block', re.DOTALL)
    AUTHOR_PARSER = (r"(>By |Photographs by |Photographs and text by )(?P<author>[^.]*)[.]", 'author', 0)
    COVER_PARSER = (r"(?P<cover>(ecx|_cache).*?[.]jpg)", 'cover', 0)
    PRICE_PARSER = (r"(?P<price>\$[0-9]+[.][0-9][0-9])", 'price', 0)
    DESC_PARSER = (r"Description</span><br>(?P<desc>.*?)</font>", 'desc', re.DOTALL)
    ISBN_PARSER = (r"ISBN (?P<isbn>[0-9]+)", 'isbn', 0)
    ISBN_PARSER2 = (r"(?P<isbn>[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])", 'isbn', 0)

    def main(self):
        path = os.path.join(os.path.dirname(__file__), 'template/photoeye.html')
        
        updated = []
        q = db.GqlQuery("SELECT uid, has_preview FROM Photobook WHERE parse_error = :1 ORDER BY fetch_datetime DESC", False)
        result = q.fetch(20)
        for p in result:
            if p.has_preview:
                type = "preview"
            else:
                type = "on"

            updated.append((p.uid[9:], type))


        errors = []
        q = db.GqlQuery("SELECT uid FROM Photobook WHERE parse_error = :1 ORDER BY fetch_datetime DESC", True)
        result = q.fetch(100)
        for p in result:
            errors.append(p.uid[9:])

        searches = []
        f = open(os.path.join(os.path.dirname(__file__), 'id.txt'), 'r')
        for line in f:
            searches.append(line.strip())

        values = { 'updated' : updated, 'errors' : errors, 'searches' : searches }
        data = template.render(path, values)
        return data
        
    def table(self, key):
        items = []
        if key == 'all':
            for cx in string.ascii_uppercase:
                row = []
                for cy in string.ascii_uppercase:
                    row.append(cx + cy)
                items.append(row)
            path = os.path.join(os.path.dirname(__file__), 'template/table.html')
        else:
            book_map = {}
            q = db.GqlQuery("SELECT uid, has_preview from Photobook WHERE uid >= :1 AND uid <= :2", \
                            "photoeye."+key+"000", "photoeye."+key+"999")
            result = q.fetch(1000)
            for p in result:
                if p.has_preview:
                    book_map[p.uid[9:]] = "preview"
                else: 
                    book_map[p.uid[9:]] = "on"

            index = 0
            for i in range(0, 50):
                row = []
                for j in range(0, 20):
                    uid = key + '{:03}'.format(index)
                    row.append((uid, book_map.get(uid, "off")))
                    index += 1
                items.append(row)
 
            path = os.path.join(os.path.dirname(__file__), 'template/table_sub.html')
        
        values = { 'items' : items }
        data = template.render(path, values)
        return data

    def updated(self):
        starttime = time.time()
        logging.info("Check Updated: Start")

        headers = {'Cache-Control':'no-cache,max-age=0', 'Pragma':'no-cache'}
        result = urlfetch.fetch(self.URL_NEW_ARRIVALS, deadline=self.URL_TIMEOUT, headers=headers)
        if result.status_code != 200:
            return "Fetch Failed"

        buf = result.content
        idset = set(re.findall(self.KEY_PATTERN, buf))
            
        for id in idset:
            self.book(id)

        logging.info("Check Updated: Finished. Elapsed {}".format(time.time() - starttime))
        return idset

    def book(self, id, type="html", force=False, admin=None):
        uid = self.uid(id)
        logging.info("Get Book: {}".format(uid))
        q = db.GqlQuery("SELECT * from Photobook WHERE uid = :1", uid)
        result = q.fetch(1)
        if len(result) == 0 or force == True:
            try:
                if len(result) > 0:
                    db.delete(result[0].key())
                result = self.get_book(self.id(uid))
            except:
                self.error(uid, traceback.format_exc())
                result = "[ERROR] Parse Error"

            return result
        
        if type == "html": 
            path = os.path.join(os.path.dirname(__file__), 'template/book.html')
            values = { 'book' : result[0], 'admin' : admin }
            data = template.render(path, values)
        else:
            data = result[0].to_xml()

        return data

    def thumbnail(self, id):
        uid = self.uid(id)
        logging.info("Get Thumbnail: {}".format(uid))
        q = db.GqlQuery("SELECT * from Photobook WHERE uid = :1", uid)
        result = q.fetch(1)
        if len(result) != 0:
            return result[0].cover_thumbnail
        return None

    def error(self, uid, trace):
        book = {}
        book['uid'] = uid
        book['parse_error'] = True
        book['desc'] = trace
        book['links'] = [ self.URL_BOOK + self.id(uid) ]
        logging.error(book['desc'])
        self.put(book)

    def list_year(self, year, start=0, count=0):
        logging.info("Get List Year: year={} start={} count={}".format(year, start, count))
        q = db.GqlQuery("SELECT * from Photobook WHERE year = :1", int(year))
        result = q.fetch(100)

        path = os.path.join(os.path.dirname(__file__), 'template/list.html')
        values = { 'books' : result }
        data = template.render(path, values)
        
        return data

    def get_book(self, id):
        logging.info("Get Book: {}".format(id))
        if id == '':
            return "Invalid ID"

        book = {}
        result = urlfetch.fetch(self.URL_BOOK + id, deadline=self.URL_TIMEOUT)
        if result.status_code != 200:
            return "Fetch Failed"

        buf = result.content
        book['uid'] = self.MODULE + '.' + id
        book['source_url'] = self.URL_BOOK + id
        book['links'] = []
        book['links'].append(book['source_url'])
        book['title'] = self._extract(self.TITLE_PARSER, buf)
        if not book['title']:
            return 'Not Exist'

        book['photographer'] = self._extract(self.AUTHOR_PARSER, buf)
        block = self._extract(self.BLOCK_PARSER, buf)
        block_list = [item.strip() for item in re.split("[,.]\W+", block)]
        book['publisher'] = block_list[0]
        while not block_list[1].isdigit(): 
            book['publisher'] += ", " + block_list.pop(1)
        book['year'] = int(block_list[1])
        book['pages'] = block_list[2].replace('pp', '').strip()
        if book['pages'] == 'Unpaged':
            book['pages'] = 0
        else:
            book['pages'] = int(book['pages'])
        if len(block_list) < 5:
            block_list.append(block_list[3])
        size = re.sub(r"<[^<]*?/?>", "", block_list[4]).split("x")
        book['width'] = self._calc_size(size[0])
        book['height'] = self._calc_size(size[1])

        cover_url = self._extract(self.COVER_PARSER, buf)
        if cover_url:
            if cover_url[0:3] == 'ecx':
                book['cover_url'] = "http://" + cover_url
            else:
                book['cover_url'] = self.URL + "/" + cover_url

            # store cover and thumbnail
            book['cover'] = self._blob_url(book['cover_url'])
            book['cover_thumbnail'] = self._blob_url(book['cover_url'], resize=140) 

        book['desc'] = self._extract(self.DESC_PARSER, buf)
        if book['desc']:
            book['desc'] = book['desc'].replace('\r\n', '\n')
            book['desc'] = book['desc'].replace('<BR>', '')
        book['price'] = self._extract(self.PRICE_PARSER, buf)

        book['isbn10'] = self._extract(self.ISBN_PARSER, buf)
        if not book['isbn10']:
            book['isbn10'] = self._extract(self.ISBN_PARSER2, buf)
            
        if book['isbn10']:
            amazon_info = amazon.get_book(book['isbn10'])
            if amazon_info:
                book['links'].append(amazon_info['source_url'])
                for item in amazon_info:
                    if item not in book or not book[item]:
                        book[item] = amazon_info[item]
        # author
        if not book['author']:
            book['author'] = []
        if book['photographer'] and not book['photographer'] in book['author']:
            book['author'].insert(0, book['photographer'].decode('utf-8'))
        
        # Book Tease
        if buf.find("teaselight") >= 0: 
            book['has_preview'] = True

            preview_list = []
            index = 0
            while True:
                found = False
                index += 1
                p_url = self.URL_TEASE + "{}&image={}".format(id, str(index))
                result = urlfetch.fetch(p_url, deadline=self.URL_TIMEOUT, \
                                        headers={'Referer': p_url})
                if result.status_code == 200:
                    url = self._extract(self.COVER_PARSER, result.content)
                    if url:
                        preview_list.append((self.URL + "/" + url).decode('utf-8'))
                        logging.info("  Found preview image #{}".format(index))
                        found = True

                if not found:
                    break
            book['previews'] = preview_list
        else:
            book['has_preview'] = False

        book['parse_error'] = False
        self.put(book)
        return book

    def put(self, data):
        if not 'uid' in data:
            return "ERROR"

        book = Photobook(uid=data['uid'])
        for item in data:
            if type(data[item]) == type(''):
                data[item] = data[item].decode('utf-8')
            setattr(book, item, data[item])
        book.put()

    def uid(self, id):
        if not id.startswith(self.MODULE):
            result = self.MODULE + "." + id
        else:
            result = id
        return result
 
    def id(self, uid):
        if uid.startswith(self.MODULE):
            result = uid.replace(self.MODULE + ".", '')
        else:
            result = id
        return result
    
    def _blob_data(self, data):
        filename = files.blobstore.create(mime_type='image/jpeg')
        with files.open(filename, 'a') as f:
            f.write(data)
        files.finalize(filename)
        blob_key = files.blobstore.get_blob_key(filename)
        return blob_key

    def _blob_url(self, url, resize=0):
        result = urlfetch.fetch(url, deadline=self.URL_TIMEOUT)
        if result.status_code != 200:
            return None
        buf = result.content

        if resize != 0:
            img = images.Image(image_data=buf)
            img.resize(width=resize, height=resize)
            buf = img.execute_transforms(output_encoding=images.JPEG)
            
        blob_key = self._blob_data(buf)
        return blob_key
       
    def _extract(self, parser, str):
        c = re.compile(parser[0], parser[2])
        m = c.search(str)
        if m:
            return m.group(parser[1]).strip()
        return None

    def _calc_size(self, str):
        str = str.strip('".')
        str = str.replace('&frac14;', '.25')
        str = str.replace('&frac12;', '.50')
        str = str.replace('&frac34;', '.75')
        result = float(str) * 25.4
        return int(result)

photoeye = Photoeye()

if __name__ == "__main__":
    photoeye.get_book("ZE657")
    photoeye.get_book("ZE873")
    b = photoeye.get_book("ZE850")
    photoeye.put(b)
