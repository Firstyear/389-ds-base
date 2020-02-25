# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2020 William Brown <william@blackhats.net.au>
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#

import os
import logging
import ldap.schema
from ldif import LDIFParser
from lib389.utils import ensure_list_str

logger = logging.getLogger(__name__)

class SimpleParser(LDIFParser):
    def __init__(self, f):
        self.entries = []
        super().__init__(f)
        pass

    def handle(self, dn, entry):
        self.entries.append((dn, entry))


def ldif_parse(path, rpath):
    with open(os.path.join(path, rpath), 'r') as f:
        sp = SimpleParser(f)
        sp.parse()
        return sp.entries

def db_cond(name):
    if name == 'olcDatabase={0}config.ldif':
        return False
    if name == 'olcDatabase={-1}frontend.ldif':
        return False
    if name.startswith('olcDatabase=') and name.endswith('.ldif'):
        return True
    return False


class olOverlay(object):
    def __init__(self, path, name, log):
        self.log = log
        self.log.debug(f"olOverlay path -> {path}/{name}")
        entries = ldif_parse(path, name)
        assert len(entries) == 1
        self.config = entries.pop()
        self.log.debug(f"{self.config}")

class olDatabase(object):
    def __init__(self, path, name, log):
        self.log = log
        self.log.debug(f"olDatabase path -> {path}")
        entries = ldif_parse(path, f'{name}.ldif')
        assert len(entries) == 1
        self.config = entries.pop()
        self.log.debug(f"{self.config}")

        overlay_path = os.path.join(path, name)
        self.overlays = [
            olOverlay(overlay_path, x, log)
            for x in sorted(os.listdir(overlay_path))
        ]

# See https://www.python-ldap.org/en/latest/reference/ldap-schema.html
class olAttribute(ldap.schema.models.AttributeType):
    def __init__(self, value, log):
        self.log = log
        self.log.debug(f"olAttribute value -> {value}")
        # This split takes {0}(stuff) and will only leave stuf.
        super().__init__(value.split('}', 1)[1])

    def __str__(self):
        self.__unicode__()

    def __unicode__(self):
        f"{self.names}"

class olClass(ldap.schema.models.ObjectClass):
    def __init__(self, value, log):
        self.log = log
        self.log.debug(f"olClass value -> {value}")
        super().__init__(value.split('}', 1)[1])

    def __str__(self):
        self.__unicode__()

    def __unicode__(self):
        f"{self.names}"

class olSchema(object):
    def __init__(self, path, log):
        self.log = log
        self.log.debug(f"olSchema path -> {path}")
        schemas = sorted(os.listdir(path))
        self.log.debug(f"olSchemas -> {schemas}")

        self.raw_schema = []

        for schema in schemas:
            entries = ldif_parse(path, schema)
            assert len(entries) == 1
            self.raw_schema.append(entries.pop())
        # self.log.debug(f"raw_schema -> {self.raw_schema}")

        self.raw_attrs = []
        self.raw_classes = []

        for (cn, rs) in self.raw_schema:
            self.raw_attrs += ensure_list_str(rs['olcAttributeTypes'])
            self.raw_classes += ensure_list_str(rs['olcObjectClasses'])

        self.attrs = [olAttribute(x, self.log) for x in self.raw_attrs]
        self.classes = [olClass(x, self.log) for x in self.raw_classes]
        self.log.debug(f'attrs -> {self.attrs}')
        self.log.debug(f'classes -> {self.classes}')



class olConfig(object):
    def __init__(self, path, log=None):
        self.log = log
        if self.log is None:
            self.log = logger
        self.log.debug(f"olConfig path -> {path}")
        config_entries = ldif_parse(path, 'cn=config.ldif')
        assert len(config_entries) == 1
        self.config_entry = config_entries.pop()
        self.log.debug(self.config_entry)

        # Parse all the child values.
        self.schema = olSchema(os.path.join(path, 'cn=config/cn=schema/'), self.log)

        dbs = sorted([
            os.path.split(x)[1].replace('.ldif', '')
            for x in os.listdir(os.path.join(path, 'cn=config'))
            if db_cond(x)
        ])
        self.log.debug(f"olDatabases -> {dbs}")

        self.databases = [
            olDatabase(os.path.join(path, f'cn=config/'), db, self.log)
            for db in dbs
        ]
        self.log.debug('parsed olConfig')


