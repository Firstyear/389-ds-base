# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2020 William Brown <william@blackhats.net.au>
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---

import ldap
import pytest
import time
from lib389.topologies import topology_st
from lib389.backend import Backends, Backend
from lib389.mappingTree import MappingTrees
from lib389.idm.domain import Domain
from lib389.configurations.sample import create_base_domain

@pytest.fixture
def topology(topology_st):
    bes = Backends(topology_st.standalone)
    for be in bes.list():
        be.delete()
    mts = MappingTrees(topology_st.standalone)
    assert len(mts.list()) == 0
    return topology_st


def create_backend(inst, rdn, suffix):
    # We only support dc= in this test.
    assert suffix.startswith('dc=')
    be1 = Backend(inst)
    be1.create(properties={
            'cn': rdn,
            'nsslapd-suffix': suffix,
        },
        create_mapping_tree=False
    )

    # Now we temporarily make the MT for this node so we can add the base entry.
    mts = MappingTrees(inst)
    mt = mts.create(properties={
        'cn': suffix,
        'nsslapd-state': 'backend',
        'nsslapd-backend': rdn,
    })

    # Create the domain entry
    create_base_domain(inst, suffix)
    # Now delete the mt
    mt.delete()

    return be1

def test_mapping_tree_inverted(topology):
    """

    :id: 024c4960-3aac-4d05-bc51-963dfdeb16ca

    :setup: Standalone instance

    :steps:
        1. Do Crimes
        2. ???
        3. Exceptions, maybe.
        4. Run from the LDAP police

    :expectedresults:
        1. Don't get arrested
        2. Do not get arrested
        3. DONT GET ARRESTORED
        4. 🚨🚨🚨
    """
    inst = topology.standalone
    # First create two Backends, without mapping trees.
    be1 = create_backend(inst, 'userRootA', 'dc=example,dc=com')
    be2 = create_backend(inst, 'userRootB', 'dc=straya,dc=example,dc=com')
    # Okay, now we create the mapping trees for these backends, and we *invert*
    # them.
    mts = MappingTrees(inst)
    mtb = mts.create(properties={
        'cn': 'dc=straya,dc=example,dc=com',
        'nsslapd-state': 'backend',
        'nsslapd-backend': 'userRootB',
    })
    mta = mts.create(properties={
        'cn': 'dc=example,dc=com',
        'nsslapd-state': 'backend',
        'nsslapd-backend': 'userRootA',
        'nsslapd-parent-suffix': 'dc=straya,dc=example,dc=com'
    })
    # I'm not sure I'm willing to actually search this absolutely terrifying creation ...
    # what ends up occuring is uhhh ... interesting. Both backends end up not working.
    #
    # First the node for dc=straya is hung attached to the root mt node.
    # Then we call mapping_tree_node_get_children with is_root = 0, and we find
    # "(&(objectclass=nsMappingTree)(|(nsslapd-parent-suffix=\"dc=straya,dc=example,dc=com\")(nsslapd-parent-suffix=dc=straya,dc=example,dc=com)))"
    # This lets us find dc=example.
    # This is dutifiully added, with no check about the ordering and logic.
    #
    # So our MT now is:
    # "" -> dc=straya,ec -> dc=example,c
    # As you can see, a bit "broken".
    #
    # When a search is then performed we call: slapi_mapping_tree_select_all -> slapi_get_mapping_tree_node_by_dn -> best_matching_child
    # 
    # This explains why dc=example,dc=com is broken - issuffix in best_matching_child will never
    # succeed because dc=straya is greater, and so ec will never be reached. The server believes no suffix exists.
    #
    # Why dc=straya fails is harder to understand. MT *is* able to find the MT node, in slapi_get_mapping_tree_node_by_dn
    # but because of how the loop is performed, next_best_match then examines the children which includes
    # the mt of dc=example. Because this has issuffix pass, this then returns that. This means that the
    # query for dc=straya is *incorrectly* routed to userRootA.

    dc_ex = Domain(inst, dn='dc=example,dc=com')
    assert dc_ex.exists()

    dc_st = Domain(inst, dn='dc=straya,dc=example,dc=com')
    assert dc_st.exists()


def test_mapping_tree_nonexist_parent(topology):
    """

    :id: 7a9a09bd-7604-48f7-93cb-abff9e0d0131

    :setup: Standalone instance

    :steps:
        1. ???

    :expectedresults:
        1. Success
    """
    inst = topology.standalone
    be1 = create_backend(inst, 'userRootA', 'dc=example,dc=com')
    mts = MappingTrees(inst)
    mta = mts.create(properties={
        'cn': 'dc=example,dc=com',
        'nsslapd-state': 'backend',
        'nsslapd-backend': 'userRootA',
        'nsslapd-parent-suffix': 'dc=com'
    })
    # In this case the MT is never joined properly to the hierachy because the parent suffix
    # doesn't exist. The config is effectively ignored. That means that it can't be searched!
    dc_ex = Domain(inst, dn='dc=example,dc=com')
    assert dc_ex.exists()

