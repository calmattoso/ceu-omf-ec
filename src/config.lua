[[
    -- Definicao de aplicacoes
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

    -- Definicao de grupos
    groups["Sender"] = {
        nodes = {
            "omf.nicta.node8"
        },
        apps = {
            ping_app = {
                app_id = "ping_oml2",
                target = "www.nicta.com.au",
                count  = 3,
            },
        },
    }
]]
