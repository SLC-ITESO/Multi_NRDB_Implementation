#!/usr/bin/env python3
import logging

import falcon
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# Set logger
log = logging.getLogger()
log.setLevel('INFO')
handler = logging.FileHandler('multidrdb_mongo.log')
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
log.addHandler(handler)
