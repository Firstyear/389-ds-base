# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2020 William Brown <william@blackhats.net.au>
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#

from lib389.schema import Schema

class MigrationAction(object):
    def __init__(self):
        pass

    def apply(self, inst):
        raise Exception('not implemented')

    def post(self):
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
    def __init__(self, attr):
        self.attr = attr

    def __unicode__(self):
        return f"SchemaAttributeCreate -> {self.attr.__unicode__()}"

class SchemaAttributeAdjust(MigrationAction):
    def __init__(self, attr, exist_names):
        self.exist_names = exist_names
        self.attr = attr

    def __unicode__(self):
        return f"SchemaAttributeAdjust -> {self.exist_names} to {self.attr.__unicode__()}"

class SchemaAttributeAmbiguous(MigrationAction):
    def __init__(self, attr):
        self.attr = attr

    def __unicode__(self):
        return f"SchemaAttributeAdjust -> {self.attr.__unicode__()}"

class SchemaClassCreate(MigrationAction):
    def __init__(self, obj):
        self.obj = obj

    def __unicode__(self):
        return f"SchemaClassCreate -> {self.obj.__unicode__()}"

class SchemaClassAdjust(MigrationAction):
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
            buff += f"{item.__unicode__()}\n"
        return buff

    def _gen_migration_plan(self):
        """Order of this module is VERY important!!!
        """
        # Get the server schema so that we can query it repeatedly.
        schema = Schema(self.inst)
        schema_attrs = schema.get_attributetypes()
        schema_attr_names = dict([
            (set([x.lower() for x in attr.names]), attr)
            for attr in schema_attrs
        ])

        schema_objects = schema.get_objectclasses()
        schema_object_names = dict([
            (set([x.lower() for x in obj.names]), obj)
            for obj in schema_objects
        ])

        # Examine schema attrs
        for attr in self.olconfig.schema.attrs:
            # For the attr, find if anything has a name overlap in any capacity.
            overlaps = [ a for a in schema_attr_names.keys() if len(a.intersection(attr.name_set)) > 0]
            if len(overlaps) == 0:
                # We need to add attr
                self.plan.append(SchemaAttributeCreate(attr))
            elif len(overlaps) == 1:
                # We need to possibly adjust attr
                exist_attr = overlaps[0]
                diff = attr.name_set.difference(exist_attr)
                if len(diff) > 0:
                    self.plan.append(SchemaAttributeAdjust(attr, exist_attr))
            else:
                # Ambiguous attr, the admin must intervene
                self.plan.append(SchemaAttributeAmbiguous(attr))

        # Examine schema classes
        for obj in self.olconfig.schema.classes:
            # For the attr, find if anything has a name overlap in any capacity.
            overlaps = [ o for o in schema_object_names.keys() if len(o.intersection(obj.name_set)) > 0]
            if len(overlaps) == 0:
                # We need to add attr
                self.plan.append(SchemaClassCreate(obj))
            elif len(overlaps) == 1:
                # We need to possibly adjust the objectClass as it exists
                pass


        # Enable plugins (regardless of db)

        # Create/Manage dbs

        # Import data

        pass







