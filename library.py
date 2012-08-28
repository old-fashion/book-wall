from google.appengine.ext import db

from photobook import *

class Library():
    def listall(self):
        q = Photobook.all()
        results = q.fetch(100)
        result = ""
        for p in results:
            result += p.to_xml()
        return result

library = Library()

if __name__ == "__main__":
    print library.listall()
