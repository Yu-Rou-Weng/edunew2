function all
{
    git submodule init
    git submodule update --recursive
    docker-compose build
}

function config
{
    # iottalk config
    docker run --name tmp-iottalk -d iottalk
    docker cp tmp-iottalk:/iottalk/conf/iottalk.ini ./iottalk/conf/iottalk.ini.sample
    docker rm -f tmp-iottalk
    # iottalk autogen config
    docker run --name tmp-autogen -d autogen
    docker cp tmp-autogen:/iottalk-autogen/_/env/.env.example ./iottalk/conf/autogen_env.example
    docker rm -f tmp-autogen
    # simtalk config
    docker run --name tmp-simtalk -d simtalk
    docker cp tmp-simtalk:/simtalk/_/env/.env.example ./iottalk/conf/simtalk_env.example
    docker rm -f tmp-simtalk
    # mosquitto config
    docker run --name tmp-mosquitto -d eclipse-mosquitto:2.0.10
    docker cp tmp-mosquitto:/mosquitto/config/mosquitto.conf ./mosquitto/mosquitto.conf.sample
    docker rm -f tmp-mosquitto
    # nginx config
    docker run --name tmp-nginx -d nginx:1.15.11-alpine
    docker cp tmp-nginx:/etc/nginx/nginx.conf ./nginx/nginx.conf.sample
    docker rm -f tmp-nginx
}

function up
{
    git -C iottalk-core        checkout master
    git -C iottalk-core        pull
    git -C iottalk-classic-gui checkout master
    git -C iottalk-classic-gui pull
    git -C iottalk-autogen     checkout master
    git -C iottalk-autogen     pull
    git -C simtalk             checkout master
    git -C simtalk             pull
}

function initdb
{
    docker-compose up -d
    docker-compose exec ccm iotctl -c /iottalk/conf/iottalk.ini initdb ccm
    docker-compose exec autogen python manage.py migratesites
    docker-compose exec simtalk python manage.py migrate
    docker-compose down
}

Try
{
    if($args.Length -eq 0) { all; } else { & $args[0] }
}
Catch [System.Management.Automation.CommandNotFoundException]
{
    Write-Host "command not found";
}

