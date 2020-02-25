# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2020 William Brown <william@blackhats.net.au>
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#

class MigrationAction(object):
    def __init__(self):
        pass

    def apply(self, inst):
        raise Exception('not implemented')

    def __unicode__(self):
        raise Exception('not implemented')


class DatabaseCreate(MigrationAction):
    pass

class DatabaseDelete(MigrationAction):
    pass

class DatabaseIndexCreate(MigrationAction):
    pass

class SchemaAttributeCreate(MigrationAction):
    pass

class SchemaClassCreate(MigrationAction):
    pass

class PluginMemberOfEnable(MigrationAction):
    pass

class PluginMemberOfConfigure(MigrationAction):
    pass

class PluginRefintEnable(MigrationAction):
    pass

class PluginRefintConfigure(MigrationAction):
    pass

class PluginUnqiueConfigure(MigrationAction):
    pass


class Migration(object):
    # Given an openldap config, we generate a set of migration actions
    # that we store and then execute in order.
    def __init__(self, olconfig, inst):
        self.olconfig = olconfig
        self.inst = inst
        self.plan = []
        self._gen_migration_plan()

    def __unicode__(self):
        buff = ""
        for item in self.plan:
            buff += "{item}\n"
        return buff

    def _gen_migration_plan(self):
        """Order of this module is VERY important!!!
        """
        # Examine schema attrs
        # Examine schema classes

        # Enable plugins (regardless of db)

        # Create/Manage dbs

        # Import data

        pass







