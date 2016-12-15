require 'src/lua_utils'
require 'src/apps'

-- res_index -> node_id
omf_inverse_node_lookup = {}

-- app_instance_id -> group_id
omf_app_to_group_lookup = {}

-- maps hrn to its type
omf_hrn_type = {}

-- Global controller "class" to manage groups
Group = {

    res_index_c = 0,

    -- Turns `group_id`s nodes array into a table for node states
    setup_group = function(group_id)
        groups[group_id].node_ids = table.clone(groups[group_id].nodes)
        groups[group_id].nodes = {}
    end,

    -- Stores a local copy of the user groups, if first call
    -- Then, for each resource in `group_id`, creates a state table
    setup_node = function(group_id, node_id)
        -- Create a table to store the state of each node
        groups[group_id].nodes[node_id] = {
            is_up     = false,
            res_index = Group.res_index_c,
            apps      = {},
            -- Future work: add network interfaces
        }
        omf_inverse_node_lookup[Group.res_index_c] = {
            name  = node_id,
            group = group_id,
        }
        Group.res_index_c = Group.res_index_c + 1
    end,

    -- Creates the states for all instances of an app in a group.
    -- For that it must traverse over the array of resources and
    -- create a state for the app in the state of each node.
    --
    -- @param `group_id`: id of the target group
    -- @param `app_instance_id`: id for the app instance in the group
    make_application = function(group_id, app_instance_id)
        app_state = {}

        -- node = groups[group_id].nodes[node_id]-- fetch node_id table
        app_state     = Application.make_application(groups[group_id].apps[app_instance_id])
        app_state.hrn = app_instance_id -- following what OMF produces in ruby        
        -- create the hrn: group_id.node_id.app_instance_id
    
        omf_app_to_group_lookup[app_instance_id] = group_id
        omf_hrn_type[app_instance_id] = "application"
        return app_state 
    end,

    -- Helper function that returns an array of all group ids
    get_group_ids = function()
        group_ids = {}
        for group_id,_ in pairs(groups) do
            table.insert(group_ids, group_id)
        end
        return group_ids
    end,
}

-- GROUPS_LUA_TEST = true
if GROUPS_LUA_TEST then
    groups = {}
    groups["Sender"] = {
        nodes = {
            "omf.nicta.node8",
            "omf.nicta.node9",
            "omf.nicta.node10",
        },
        apps = {
            ping_app = {
                app_id = "ping_oml2",
                target = "www.nicta.com.au",
                count  = 3,
            },
        },
    }

    Group.setup_group("Sender")
    table.print(groups)

    print()
    print("Setup each node")
    for _, node_id in ipairs(groups["Sender"].node_ids) do
        Group.setup_node("Sender", node_id)
    end
    table.print(groups)

    print()
    print("Make applications")
    app_state = Group.make_application("Sender", "ping_app")
    table.print(app_state)
end
