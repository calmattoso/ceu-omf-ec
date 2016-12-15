require 'src/lua_utils'

-- Controller for applications
Application = {
    -- Creates a state table for a new instance of an app
    -- `app_def`: definition of the app instance being created
    make_application = function(app_def)
        -- Future Work: Check app instantiation matches its properties
        local app_state          = table.clone(app_def)
        app_state.is_alive = false -- has the app started and is running?

        return app_state
    end,

    -- Given an app state, return its OMF parameters table
    get_parameters = function(app_state)
        -- Base it on the app spec, flattening props
        local parameters = table.clone(apps[app_state.app_id])
        
        parameters["parameters"] = {}
        for param,def in pairs(parameters.props) do
            parameters["parameters"][param] = table.clone(def)
            parameters["parameters"][param].cmd = parameters["parameters"][param].command
            parameters["parameters"][param].command = nil
        end
        parameters.props = nil

        -- Now add the user values to it
        for param,value in pairs(app_state) do
            if param ~= "app_id" and param ~= "is_alive" and param ~= "hrn" then
                parameters["parameters"][param].value = value 
            end 
        end

        return parameters
    end,
}

-- APPLICATION_LUA_TEST = true
if APPLICATION_LUA_TEST then
    apps = {}

    apps["ping_oml2"] = {
        -- Meta-atributos
        description = "Simple Definition for the ping-oml2 application",
        binary_path = "/usr/bin/ping-oml2",
        -- Atributos da aplicacao
        props = {
            target = {
                description = "Address to ping",
                command     = "-a",    
            },
            count = {
                description = "Number of times to ping",
                command     = "-c",
            },
        },
        -- Metricas nao foram implementadas...
    }

    app_def = {
        app_id = "ping_oml2",
        target = "www.nicta.com.au",
        count  = 3,
    }

    -- Test creation of app state
    app_state = Application.make_application(app_def)
    table.print(app_state)

    -- Test creation of parameters table
    print()
    print("Parameters")
    table.print(Application.get_parameters(app_state))
    print(JSON:encode(Application.get_parameters(app_state)))
end
