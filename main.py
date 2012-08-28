#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import os
import json

from google.appengine.api import taskqueue
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import blobstore_handlers

from photoeye import *
from amazon import *
from library import *

class MainHandler(webapp2.RequestHandler):
    def get(self):
        values = { 'name' : 'jongmin' }
        path = os.path.join(os.path.dirname(__file__), 'template/index.html')
        self.response.out.write(template.render(path, values))

class PhotoeyeHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(photoeye.main())

class BookHandler(webapp2.RequestHandler):
    def get(self, id):
        admin = self.request.get('admin')
        force = (self.request.get('force', "False") == "True")
        type = self.request.get('type', "html")

        self.response.headers['Content-Type'] = 'text/' + type
        self.response.out.write(photoeye.book(id=id, type=type, force=force, admin=admin))

class ThumbnailHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, id):
        blob_info = photoeye.thumbnail(id)
        self.send_blob(blob_info, content_type='image/jpeg')

class Book2Handler(webapp2.RequestHandler):
    def get(self):
        id = self.request.get('id')
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(json.dumps(amazon.get_book(id)))

class ListHandler(webapp2.RequestHandler):
    def get(self, key, value):
        if key == 'year':
            data = photoeye.list_year(value)
        
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(data)
        #self.response.out.write(library.listall())

class UpdatedHandler(webapp2.RequestHandler):
    def get(self):
        taskqueue.add(url='/updated_worker')
        self.response.out.write("Updated job queued")

class UpdatedWorkerHandler(webapp2.RequestHandler):
    def post(self):
        self.response.out.write(photoeye.updated())

class TableHandler(webapp2.RequestHandler):
    def get(self):
        key = self.request.get('key')
        if not key:
            key = 'all'
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(photoeye.table(key))

class ErrorHandler(webapp2.RequestHandler):
    def get(self, id):
        self.response.out.write(photoeye.error(id, trace="Admin registerred"))

app = webapp2.WSGIApplication([
    ('/', MainHandler), 
    ('/photoeye', PhotoeyeHandler),
    ('/book/([^/]+)?', BookHandler),
    ('/cover/thumbnail/([^/]+)?', ThumbnailHandler),
    ('/cover/([^/]+)?', ThumbnailHandler),
    ('/isbn', Book2Handler),
    ('/table', TableHandler),
    ('/list/([^/]+)/([^/]+)?', ListHandler),
    ('/updated', UpdatedHandler),
    ('/updated_worker', UpdatedWorkerHandler),
    ('/error/([^/]+)?', ErrorHandler)
], debug=True)

