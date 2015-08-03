#!/usr/bin/env python

# kb_builder builts keyboard plate and case CAD files using JSON input.
# 
# Copyright (C) 2015  Will Stevens (swill)
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import lib.builder as builder
import hashlib
import json
import logging
import pprint
import time
import tornado.gen
import tornado.httpclient
import tornado.ioloop
import tornado.options
import tornado.web

from config import config

builder_timeout = 7200

class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')

    @tornado.gen.coroutine
    def post(self):
        data = json.loads(self.request.body)
        data_hash = hashlib.sha1(json.dumps(data, sort_keys=True)).hexdigest()
        cad = {}
        build_start = time.time()
        logging.info("Processing: %s" % (data_hash))
        cad = builder.build(data_hash, data, config, logging.getLogger())
        logging.info("Finished: %s" % (data_hash))
        logging.info("Processing took: {0:.2f} seconds".format(time.time()-build_start))
        self.write(cad)


def make_app():
    settings = {
        'template_path':'templates',
        'static_path':config['app']['static'],
        'debug':config['app']['debug']
    }
    return tornado.web.Application([
        (r"/", IndexHandler)
    ], **settings)


def main():
    tornado.options.options.log_file_prefix = config['app']['log']
    tornado.options.parse_command_line()
    logging.info("Started the kb_builder...")
    app = make_app()
    app.listen(config['app']['port'])
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
