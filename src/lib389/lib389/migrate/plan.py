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

class SchemaAttributeInconsistent(MigrationAction):
    def __init__(self, attr, ds_attr):
        self.ds_attr = ds_attr
        self.attr = attr

    def __unicode__(self):
        return f"SchemaAttributeInconsistent -> {self.ds_attr} to {self.attr.__unicode__()}"

class SchemaAttributeAmbiguous(MigrationAction):
    def __init__(self, attr):
        self.attr = attr

    def __unicode__(self):
        return f"SchemaAttributeInconsistent -> {self.attr.__unicode__()}"

class SchemaClassCreate(MigrationAction):
    def __init__(self, obj):
        self.obj = obj

    def __unicode__(self):
        return f"SchemaClassCreate -> {self.obj.__unicode__()}"

class SchemaClassInconsistent(MigrationAction):
    def __init__(self, obj, ds_obj):
        self.ds_obj = ds_obj
        self.obj = obj

    def __unicode__(self):
        return f"SchemaClassInconsistent -> {self.ds_obj} to {self.obj.__unicode__()}"

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
        schema_objects = schema.get_objectclasses()

        # Examine schema attrs
        for attr in self.olconfig.schema.attrs:
            # For the attr, find if anything has a name overlap in any capacity.
            # overlaps = [ (names, ds_attr) for (names, ds_attr) in schema_attr_names if len(names.intersection(attr.name_set)) > 0]
            overlaps = [ ds_attr for ds_attr in schema_attrs if ds_attr.oid == attr.oid]
            if len(overlaps) == 0:
                # We need to add attr
                self.plan.append(SchemaAttributeCreate(attr))
            elif len(overlaps) == 1:
                # We need to possibly adjust attr
                ds_attr = overlaps[0]
                # We need to have a way to compare the two.
                if attr.inconsistent(ds_attr):
                    self.plan.append(SchemaAttributeInconsistent(attr, ds_attr))
            else:
                # Ambiguous attr, the admin must intervene to migrate it.
                self.plan.append(SchemaAttributeAmbiguous(attr, overlaps))

        # Examine schema classes
        for obj in self.olconfig.schema.classes:
            # For the attr, find if anything has a name overlap in any capacity.
            overlaps = [ ds_obj for ds_obj in schema_objects if ds_obj.oid == obj.oid]
            if len(overlaps) == 0:
                # We need to add attr
                self.plan.append(SchemaClassCreate(obj))
            elif len(overlaps) == 1:
                # We need to possibly adjust the objectClass as it exists
                ds_obj = overlaps[0]
                if obj.inconsistent(ds_obj):
                    self.plan.append(SchemaClassInconsistent(obj, ds_obj))
            else:
                # This should be an impossible state.
                raise Exception('impossible state')


        # Enable plugins (regardless of db)

        # Create/Manage dbs

        # Import data

        pass







