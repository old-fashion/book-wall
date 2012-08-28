from google.appengine.ext import db
from google.appengine.ext import blobstore

class Photobook(db.Model):
    uid = db.StringProperty(required=True, indexed=True)

    title = db.StringProperty()
    sub_title = db.StringProperty()
    trans_title = db.StringProperty()

    photographer = db.StringProperty()
    author = db.ListProperty(str)
    text = db.StringProperty()
    publisher = db.StringProperty()
    year = db.IntegerProperty()

    isbn10 = db.StringProperty()
    isbn13 = db.StringProperty()

    pages = db.IntegerProperty()
    width = db.IntegerProperty()
    height = db.IntegerProperty()
    weight = db.FloatProperty()
    thickness = db.IntegerProperty()
    extent = db.StringProperty()
    plates = db.StringProperty()
    printed = db.StringProperty()
    language = db.StringProperty()

    price = db.StringProperty()
    desc = db.TextProperty()

    cover_url = db.StringProperty()
    has_preview = db.BooleanProperty()
    previews = db.ListProperty(str)

    editions = db.ListProperty(str)
    references = db.ListProperty(str)
    links = db.ListProperty(str)

    cover = blobstore.BlobReferenceProperty()
    cover_thumbnail = blobstore.BlobReferenceProperty()
    parse_error = db.BooleanProperty()
    fetch_datetime = db.DateTimeProperty(auto_now=True)

