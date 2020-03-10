# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2020 William Brown <william@blackhats.net.au>
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#
import pytest
import os
from lib389.topologies import topology_st
from lib389.password_plugins import PBKDF2Plugin
from lib389.utils import ds_is_older

from lib389.migrate.openldap.config import olConfig
from lib389.migrate.plan import Migration
# from lib389.migrate.plan import *

pytestmark = pytest.mark.tier1

DATADIR1 = os.path.join(os.path.dirname(__file__), '../../data/openldap_2_389/1/')

@pytest.mark.skipif(ds_is_older('1.4.3'), reason="Not implemented")
def test_parse_openldap_slapdd():
    """Test parsing an example openldap configuration. We should be able to
    at least determine the backends, what overlays they have, and some other
    minimal amount.

    :id: b0061ab0-fff4-45c6-b6c6-171ca3d2dfbc
    :setup: Data directory with an openldap config directory.
    :steps:
        1. 
    :expectedresults:
        1. 
    """
    config_path = os.path.join(DATADIR1, 'slapd.d')
    config = olConfig(config_path)

    # Do we have databases?
    assert len(config.databases) == 2

    # Did our schema parse?
    assert any(['suseModuleConfiguration' in x.names for x in config.schema.classes])


@pytest.mark.skipif(ds_is_older('1.4.3'), reason="Not implemented")
def test_migrate_openldap_slapdd(topology_st):
    """

    :id: e9748040-90a0-4d69-bdde-007104f75cc5
    :setup: 
    :steps:
        1. 
    :expectedresults:
        1. 
    """

    inst = topology_st.standalone
    config_path = os.path.join(DATADIR1, 'slapd.d')
    config = olConfig(config_path)
    ldifs = {
        "dc=example,dc=com": os.path.join(DATADIR1, 'example_com.slapcat.ldif'),
        "dc=example,dc=net": os.path.join(DATADIR1, 'example_net.slapcat.ldif'),
    }

    migration = Migration(config, inst, ldifs)

    print(migration.__unicode__())

    migration.execute_plan()




