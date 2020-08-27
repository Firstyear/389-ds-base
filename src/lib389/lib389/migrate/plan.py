# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2020 William Brown <william@blackhats.net.au>
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#

from lib389.schema import Schema, Resolver
from lib389.backend import Backends
from lib389.migrate.openldap.config import olOverlayType
from lib389.plugins import MemberOfPlugin, ReferentialIntegrityPlugin, AttributeUniquenessPlugins
import ldap
import os
from ldif import LDIFParser
from ldif import LDIFWriter
from uuid import uuid4

class MigrationAction(object):
    def __init__(self):
        pass

    def apply(self, inst):
        raise Exception('not implemented')

    def post(self):
        pass
        # raise Exception('not implemented')

    def __unicode__(self):
        raise Exception('not implemented')


class DatabaseCreate(MigrationAction):
    def __init__(self, suffix, uuid):
        self.suffix = suffix
        self.uuid = uuid

    def apply(self, inst):
        bes = Backends(inst)
        be = bes.create(properties={
            'cn': self.uuid,
            'nsslapd-suffix': self.suffix,
        })

    def __unicode__(self):
        return f"DatabaseCreate -> {self.suffix}, {self.uuid}"

class DatabaseIndexCreate(MigrationAction):
    def __init__(self, suffix, olindex):
        self.suffix = suffix
        self.attr = olindex[0]
        # Will this work with multiple index types
        self.type = olindex[1]

    def apply(self, inst):
        be = Backends(inst).get(self.suffix)
        indexes = be.get_indexes()
        try:
            # If it exists, return. Could be the case as we created the
            # BE and the default indexes applied now.
            indexes.get(self.attr)
            return
        except ldap.NO_SUCH_OBJECT:
            pass
        be.add_index(self.attr, self.type)

    def __unicode__(self):
        return f"DatabaseIndexCreate -> {self.attr} {self.type}, {self.suffix}"

class DatabaseReindex(MigrationAction):
    def __init__(self, suffix):
        self.suffix = suffix

    def apply(self, inst):
        bes = Backends(inst)
        be = bes.get(self.suffix)
        be.reindex(wait=True)

    def __unicode__(self):
        return f"DatabaseReindex -> {self.suffix}"

class ImportTransformer(LDIFParser):
    def __init__(self, f_import, f_outport):
        self.f_outport = f_outport
        self.writer = LDIFWriter(self.f_outport)
        super().__init__(f_import)

    def handle(self, dn, entry):
        attrs = entry.keys()
        # We don't know what form the keys/attrs are in
        # so we have to establish our own map of our
        # idea of these to the attrs idea.
        amap = dict([(x.lower(), x) for x in attrs])

        # Now we can do transforms
        # This has to exist ....
        oc_a = amap['objectclass']
        # If mo present, as nsMemberOf.
        try:
            mo_a = amap['memberof']
            # If mo_a was found, then mo is present, extend the oc.
            entry[oc_a] += [b'nsMemberOf']
        except:
            # Not found
            pass

        # strip entryCSN
        try:
            ecsn_a = amap['entrycsn']
            entry.pop(ecsn_a)
        except:
            # No ecsn, skip
            pass

        # strip sco
        try:
            sco_a = amap['structuralobjectclass']
            entry.pop(sco_a)
        except:
            # No sco, skip
            pass

        # Write it out
        self.writer.unparse(dn, entry)

class DatabaseLdifImport(MigrationAction):
    def __init__(self, suffix, ldif_path):
        self.suffix = suffix
        self.ldif_path = ldif_path

    def apply(self, inst):
        # Create a unique op id.
        op_id = str(uuid4())
        op_path = os.path.join(inst.get_ldif_dir(), f'{op_id}.ldif')

        with open(self.ldif_path, 'r') as f_import:
            with open(op_path, 'w') as f_outport:
                p = ImportTransformer(f_import, f_outport)
                p.parse()

        ### time.sleep?

        be = Backends(inst).get(self.suffix)
        task = be.import_ldif([op_path])
        task.wait()

    def __unicode__(self):
        return f"DatabaseLdifImport -> {self.suffix} {self.ldif_path}"

class SchemaAttributeUnsupported(MigrationAction):
    def __init__(self, attr):
        self.attr = attr

    def __unicode__(self):
        return f"SchemaAttributeUnsupported -> {self.attr.__unicode__()}"

    def apply(self, inst):
        inst.log.debug(f"SchemaAttributeUnsupported -> {self.attr.__unicode__()} (SKIPPING)")

class SchemaAttributeCreate(MigrationAction):
    def __init__(self, attr):
        self.attr = attr

    def __unicode__(self):
        return f"SchemaAttributeCreate -> {self.attr.__unicode__()}"

    def apply(self, inst):
        schema = Schema(inst)
        inst.log.debug("SchemaAttributeCreate -> %s" % self.attr.schema_str())
        schema.add(self.attr.schema_attribute, self.attr.schema_str())

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

class SchemaClassUnsupported(MigrationAction):
    def __init__(self, obj):
        self.obj = obj

    def __unicode__(self):
        return f"SchemaClassUnsupported -> {self.obj.__unicode__()}"

    def apply(self, inst):
        inst.log.debug(f"SchemaClassUnsupported -> {self.obj.__unicode__()} (SKIPPING)")

class SchemaClassCreate(MigrationAction):
    def __init__(self, obj):
        self.obj = obj

    def __unicode__(self):
        return f"SchemaClassCreate -> {self.obj.__unicode__()}"

    def apply(self, inst):
        schema = Schema(inst)
        inst.log.debug("SchemaClassCreate -> %s" % self.obj.schema_str())
        schema.add(self.obj.schema_attribute, self.obj.schema_str())

class SchemaClassInconsistent(MigrationAction):
    def __init__(self, obj, ds_obj):
        self.ds_obj = ds_obj
        self.obj = obj

    def __unicode__(self):
        return f"SchemaClassInconsistent -> {self.ds_obj} to {self.obj.__unicode__()}"

class PluginMemberOfEnable(MigrationAction):
    def __init__(self):
        pass

    def apply(self, inst):
        mo = MemberOfPlugin(inst)
        mo.enable()
        inst.restart()

    def __unicode__(self):
        return "PluginMemberOfEnable"

class PluginMemberOfScope(MigrationAction):
    def __init__(self, suffix):
        self.suffix = suffix

    def apply(self, inst):
        mo = MemberOfPlugin(inst)
        mo.add_entryscope(self.suffix)

    def __unicode__(self):
        return f"PluginMemberOfScope -> {self.suffix}"

class PluginMemberOfFixup(MigrationAction):
    def __init__(self, suffix):
        self.suffix = suffix

    def apply(self, inst):
        mo = MemberOfPlugin(inst)
        task = mo.fixup(self.suffix)
        task.wait()

    def __unicode__(self):
        return f"PluginMemberOfFixup -> {self.suffix}"

class PluginRefintEnable(MigrationAction):
    def __init__(self):
        pass
        # Set refint delay to 0

    def apply(self, inst):
        rip = ReferentialIntegrityPlugin(inst)
        rip.set_update_delay(0)
        rip.enable()

    def __unicode__(self):
        return "PluginRefintEnable"

class PluginRefintAttributes(MigrationAction):
    def __init__(self, attr):
        self.attr = attr

    def apply(self, inst):
        rip = ReferentialIntegrityPlugin(inst)
        try:
            rip.add_membership_attr(self.attr)
        except ldap.TYPE_OR_VALUE_EXISTS:
            # This is okay, move on.
            pass

    def __unicode__(self):
        return f"PluginRefintAttributes -> {self.attr}"

class PluginRefintScope(MigrationAction):
    def __init__(self, suffix):
        self.suffix = suffix

    def apply(self, inst):
        rip = ReferentialIntegrityPlugin(inst)
        rip.add_entryscope(self.suffix)

    def __unicode__(self):
        return f"PluginRefintScope -> {self.suffix}"

class PluginUniqueConfigure(MigrationAction):
    # This enables and configures.
    def __init__(self, suffix, attr, uuid):
        self.suffix = suffix
        self.attr = attr
        self.uuid = uuid

    def apply(self, inst):
        aups = AttributeUniquenessPlugins(inst)
        aup = aups.create(properties={
            'cn': f'cn=attr_unique_{self.attr}_{self.uuid}',
            'uniqueness-attribute-name': self.attr,
            'uniqueness-subtrees': self.suffix,
            'nsslapd-pluginEnabled': 'on',
        })

    def __unicode__(self):
        return f"PluginUniqueConfigure -> {self.suffix}, {self.attr} {self.uuid}"

class PluginUnknownManual(MigrationAction):
    def __init__(self, overlay):
        self.overlay = overlay

    def __unicode__(self):
        return f"PluginUnknownManual -> {self.overlay.name}, {self.overlay.classes}"


class Migration(object):
    def __init__(self, olconfig, inst, ldifs=None):
        """Generate a migration plan from an openldap config, the instance to migrate too
        and an optional dictionary of { suffix: ldif_path }.

        The migration plan once generate still needs to be executed, but the idea is that
        this module connects to a UI program that can allow the plan to be reviewed and
        accepted. Plan modification is "out of scope", but possible as the array could
        be manipulated in place.
        """
        self.olconfig = olconfig
        self.inst = inst
        self.plan = []
        self.ldifs = ldifs
        self._schema_oid_do_not_migrate = set([
            # We pre-modified these as they are pretty core, and we don't want
            # them tampered with
            '2.5.4.2', # knowledgeInformation
            '2.5.4.7', # l, locality
            '2.5.4.29', # presentationAddress
            '2.5.4.30', # supportedApplication Context
            '2.5.4.42', # givenName
            '2.5.4.48', # protocolInformation
            '2.5.4.54', # dmdName
            '2.5.6.7', # organizationalPerson
            '2.5.6.9', # groupOfNames
            '2.5.6.10', # residentialPerson
            '2.5.6.12', # applicationEntity
            '2.5.6.13', # dsa
            '2.5.6.17', # groupOfUniqueNames
            '2.5.6.20', # dmd
            # We ignore all of the conflicts/changes from rfc2307 and rfc2307bis
            # as we provide rfc2307compat, which allows both to coexist.
            '1.3.6.1.1.1.1.16', # ipServiceProtocol
            '1.3.6.1.1.1.1.19', # ipHostNumber
            '1.3.6.1.1.1.1.20', # ipNetworkNumber
            '1.3.6.1.1.1.1.26', # nisMapName
            '1.3.6.1.1.1.1.28', # nisPublicKey
            '1.3.6.1.1.1.1.29', # nisSecretKey
            '1.3.6.1.1.1.1.30', # nisDomain
            '1.3.6.1.1.1.1.31', # automountMapName
            '1.3.6.1.1.1.1.32', # automountKey
            '1.3.6.1.1.1.1.33', # automountInformation
            '1.3.6.1.1.1.2.2', # posixGroup
            '1.3.6.1.1.1.2.6', # ipHost
            '1.3.6.1.1.1.2.7', # ipNetwork
            '1.3.6.1.1.1.2.9', # nisMap
            '1.3.6.1.1.1.2.11', # ieee802Device
            '1.3.6.1.1.1.2.12', # bootableDevice
            '1.3.6.1.1.1.2.13', # nisMap
            '1.3.6.1.1.1.2.14', # nisKeyObject
            '1.3.6.1.1.1.2.15', # nisDomainObject
            '1.3.6.1.1.1.2.16', # automountMap
            '1.3.6.1.1.1.2.17', # automount
            # This schema is buggy, we always skip it as we know the 389 version is correct.
            '0.9.2342.19200300.100.4.14',
        ])
        self._schema_oid_unsupported = set([
            # RFC4517 othermailbox syntax is not supported on 389.
            '0.9.2342.19200300.100.1.22',
            # The dsaquality syntax was removed in rfc4517
            '0.9.2342.19200300.100.1.49',
            # single level quality syntax is removed
            '0.9.2342.19200300.100.1.50',
            '0.9.2342.19200300.100.1.51',
            '0.9.2342.19200300.100.1.52',
            # Pilot person depends no otherMailbox
            '0.9.2342.19200300.100.4.4',
            # Pilot DSA needs dsaquality
            '0.9.2342.19200300.100.4.21',
            '0.9.2342.19200300.100.4.22',

        ])
        self._gen_migration_plan()

    def __unicode__(self):
        buff = ""
        for item in self.plan:
            buff += f"{item.__unicode__()}\n"
        return buff

    def _gen_schema_plan(self):
        # Get the server schema so that we can query it repeatedly.
        schema = Schema(self.inst)
        schema_attrs = schema.get_attributetypes()
        schema_objects = schema.get_objectclasses()

        resolver = Resolver(schema_attrs)

        # Examine schema attrs
        for attr in self.olconfig.schema.attrs:
            # If we have been instructed to ignore this oid, skip.
            if attr.oid in self._schema_oid_do_not_migrate:
                continue
            if attr.oid in self._schema_oid_unsupported:
                self.plan.append(SchemaAttributeUnsupported(attr))
                continue
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
            # If we have been instructed to ignore this oid, skip.
            if obj.oid in self._schema_oid_do_not_migrate:
                continue
            if obj.oid in self._schema_oid_unsupported:
                self.plan.append(SchemaClassUnsupported(obj))
                continue
            # For the attr, find if anything has a name overlap in any capacity.
            overlaps = [ ds_obj for ds_obj in schema_objects if ds_obj.oid == obj.oid]
            if len(overlaps) == 0:
                # We need to add attr
                self.plan.append(SchemaClassCreate(obj))
            elif len(overlaps) == 1:
                # We need to possibly adjust the objectClass as it exists
                ds_obj = overlaps[0]
                if obj.inconsistent(ds_obj, resolver):
                    self.plan.append(SchemaClassInconsistent(obj, ds_obj))
            else:
                # This should be an impossible state.
                raise Exception('impossible state')

    def _gen_be_exist_plan(self, oldb, be):
        # For each index
        indexes = be.get_indexes()
        for olindex in oldb.index:
            # Assert they exist
            try:
                indexes.get(olindex[0])
            except ldap.NO_SUCH_OBJECT:
                self.plan.append(DatabaseIndexCreate(oldb.suffix, olindex))

        # Reindex the db
        self.plan.append(DatabaseReindex(oldb.suffix))

    def _gen_be_create_plan(self, oldb):
        # Req db create
        self.plan.append(DatabaseCreate(oldb.suffix, oldb.uuid))
        # For each index
        # Assert we have the index on the db, or req it's creation
        for olindex in oldb.index:
            self.plan.append(DatabaseIndexCreate(oldb.suffix, olindex))

        # Reindex the db.
        self.plan.append(DatabaseReindex(oldb.suffix))

    def _gen_plugin_plan(self, oldb):
        for overlay in oldb.overlays:
            if overlay.otype == olOverlayType.UNKNOWN:
                self.plan.append(PluginUnknownManual(overlay))
            elif overlay.otype == olOverlayType.MEMBEROF:
                # Assert memberof enabled.
                self.plan.append(PluginMemberOfEnable())
                # Member of scope
                self.plan.append(PluginMemberOfScope(oldb.suffix))
                # Memberof fixup task.
                self.plan.append(PluginMemberOfFixup(oldb.suffix))
            elif overlay.otype == olOverlayType.REFINT:
                self.plan.append(PluginRefintEnable())
                for attr in overlay.attrs:
                    self.plan.append(PluginRefintAttributes(attr))
                self.plan.append(PluginRefintScope(oldb.suffix))
            elif overlay.otype == olOverlayType.UNIQUE:
                for attr in overlay.attrs:
                    self.plan.append(PluginUniqueConfigure(oldb.suffix, attr, oldb.uuid))
            else:
                raise Exception("Unknown overlay type, this is a bug!")


    def _gen_db_plan(self):
        # Create/Manage dbs
        # Get the set of current dbs.
        backends = Backends(self.inst)

        for db in self.olconfig.databases:
            # Get the suffix
            suffix = db.suffix
            try:
                # Do we have a db with that suffix already?
                be = backends.get(suffix)
                self._gen_be_exist_plan(db, be)
            except ldap.NO_SUCH_OBJECT:
                self._gen_be_create_plan(db)

            self._gen_plugin_plan(db)

    def _gen_import_plan(self):
        # Given external ldifs and suffixes, generate plans to handle these.
        if self.ldifs is None:
            return
        for (suffix, ldif_path) in self.ldifs.items():
            self.plan.append(DatabaseLdifImport(suffix, ldif_path))

    def _gen_migration_plan(self):
        """Order of this module is VERY important!!!
        """
        self._gen_schema_plan()
        self._gen_db_plan()
        self._gen_import_plan()


    def execute_plan(self):
        """ Do it!"""
        # First apply everything
        for item in self.plan:
            item.apply(self.inst)

        # Then do post
        for item in self.plan:
            item.post()

