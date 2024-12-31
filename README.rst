EduTalk in Docker
===============================================================================

Requirement
----------------------------------------------------------------------

- Domain Name
- Ports: 80, 443, 1883, 1884, 8883, 8884
- Ram: at least 4 GB
- CPU: at least 4 cores

Please install the following requirement at first.

- Docker 18.09+
- docker-compose 1.23+

System setting:

- `sudo sysctl -w vm.max_map_count=262144 <https://stackoverflow.com/questions/42889241/how-to-increase-vm-max-map-count>`_

Installation
----------------------------------------------------------------------

In case of installing iottalk-docker on a shared machine or VM,
the name of dir cloned will be used by ``docker-compose`` container name
generation, so the default dir name might conflict with other users.
It's recommended to change the dir name.::

    user@vm_name:~$ git clone git@github.com:IoTtalk/EduTalk-docker.git <myname>-edutalk-docker
    user@vm_name:~$ cd <myname>- edutalk -docker
    user@vm_name:~/<myname>-edutalk-docker$ sudo make
    user@vm_name:~/<myname>-edutalk-docker$ sudo make config

For Windows users, please checkout the section **Notes on Windows**.

Notes on Windows
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Docker on Windows guide is here:
https://docs.docker.com/docker-for-windows/install/

#. Please check that the system requirements are satisfied or not.
   (in the *SyStem Requirements* section)::

        - Windows 10 64-bit: Pro, Enterprise, or Education (Build 15063 or later).
        - Hyper-V and Containers Windows features must be enabled.

        The following hardware prerequisites are required to successfully run Client Hyper-V on Windows 10:
            64 bit processor with Second Level Address Translation (SLAT)
            4GB system RAM
            BIOS-level hardware virtualization support must be enabled in the BIOS settings.

#. According to `docker-settings-dialog
   <https://docs.docker.com/docker-for-windows/#docker-settings-dialog>`_.

   Please set the container mode as **Linux containers**,
   and enabled the **Shared drives** option for the iottalk-docker dir.

   E.g. Says that you have the dir located at ``C:/Users/A/kevin-iottalk-docker``,
   then please enable the option ``Shared drive C``;
   if your case is ``D:/kevin-iottalk-docker``,
   then just enable ``Shared drive D``)

#. Enable the PowerShell execution permission ``set-executionpolicy unrestricted``
   via the instructions listed on
   `this page
   <https://github.com/eapowertools/ReactivateUsers/wiki/Changing-Execution-Signing-Policy-in-Powershell>`_.


#. Actual installation commands for Windows.

   All the functions in ``Makefile`` are replaced by the PowerShell script ``build.ps1``.
   Please launch a Windows PowerShell window *run as an administrator*::

       git clone git@gitlab.com:IoTtalk/iottalk-docker.git <myname>-iottalk-docker
       cd <myname>-iottalk-docker
       build.ps1

   Also, all the ``make`` commands should be replaced by ``build.ps1``
   in the case of Windows.

   - ``make config`` -> ``build.ps1 config``
   - ``make initdb`` -> ``build.ps1 initdb``
   - ... etc.

Configuration (without SSL)
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

There are several configurations for each services.

#. mosquitto: ``./mosquitto/config/mosquitto.conf``.
   Usually, no changing required for this file.

#. nginx:
    #. ``./nginx/nginx.conf``
        - Change the setting ``worker_processes`` to match the machine core number.
        - Comment out the line ``include /etc/nginx/conf.d/mqtt.conf;``
    #. ``./nginx/conf.d/iottalk.conf``
        - Change the setting ``server_name`` to match your desired domain name,

          e.g. ``server_name example.edutalk.tw``

        - Follow the instructions in the comments if TLS connection is required.
    #. By default, the external port of nginx is ``80``.
       Change the external port in ``docker-compose.yml`` if the desired port
       is non-default.::

           nginx:
             ...
             ports:
             - <external port>:80

#. iottalk:
    #. Generate sample ini config via ``make config``
    #. The sample config is located at ``./iottalk/conf/iottalk.ini.sample``.
    #. Make a copy of ``iottalk.ini.sample`` and rename it to ``iottalk.ini``

       ``user@vm_name:~/<myname>-edutalk-docker$ sudo cp ./iottalk/conf/iottalk.ini.sample ./iottalk/conf/iottalk.ini``

    #. IoTtalk server
        #. Edit ``./iottalk/conf/iottalk.ini`` to meet the requirement.
            #. line 5 : Change ``userdir = /iottalk/data``
            #. [core-mqtt] : Modify the value in ``section``: ::

               scheme = mqtt

               host = domain name e.g host = example.edutalk.tw

               port = 1883

            #. [core-ws] : Modify the value in ``section``:

               scheme = wss

               host = ${core-mqtt:host}

               port = 8884

            #. line 60 : Change ``userdir = ${core:userdir}``
            #. line 64 : Modify ``flask-secret-key = <…>`` Note: The key cannot contain the following special characters $, {, }::

               e.g flask-secret-key = yiyiyi

            #. line 90 : Modify ``redis-host = redis``
            #. [gui-ec] : Modify the value in ``section``::

               ec-endpoint = https://example.edutalk.tw/iottalk/csm

            #. [gui-oauth2] :Create an application in the account system in advance and set up edutalk and iottalk. Modify the value in the section. Please refer to 

               https://hackmd.io/@HaohaoChang/iottalk_account_subsystem_setup_for_xtalk

               https://test.iottalk2.tw/account/ (Account/Password: iottalk/pcs54784)

               Example:

               [gui-oauth2]

               client-id = JzNPCD6uOWuCPZ5hRCNffTfpwmtjE4W3C45wAfv9

               client-secret = f8OsPyJte3WkQ5qTkLyGWxIhLqlH4s5Q1PzFX665BjMQM5W291ZqzQdNCMMKTSZnJTePO4pLFzxqY11PPqbvHdeUVNS4AcTdlAkK4OfJwyuFUbJT3UwXiNiNBxNB4bBNXTJefbGgA1XKvPWQBGWF7F9wNJUVDhIF 


                redirect-uri =  https://example.edutalk.tw/iottalk/ccm/auth/callback

                oidc-discovery-endpoint = https://test.iottalk2.tw/account/.well-known/openid-configuration

                revocation-endpoint = https://test.iottalk2.tw/account/oauth2/v1/revoke/

                introspect-endpoint = https://test.iottalk2.tw/account/oauth2/v1/introspect/
    
            #. Set Flask secret key ``flask-secret-key = <...>`` as a random generated string
               in the ``[gui]`` section.
               Note that the secret key can not contain special characters:
               ``$``, ``{``, ``}``.
            #. Set ``scheme = wss`` in the ``[gui-ws]`` section if secure MQTT over websocket is required.
            #. Set ``port = 8884`` in the ``[gui-ws]`` section if secure MQTT over websocket is required.
            #. Set ``ec-endpoint = http[s]://<your.public.ip.or.domain>/csm`` in the ``[gui-ec]`` section.
            #. Change other setting if needed.
    #. AutoGen
        #. Edit ``./iottalk/conf/autogen_env`` to meet the requirement.
            #. Set the database configs. The DB use sqlite3 by default. You can use autogen without any changes, but you may lose information when rebuilding or restarting. We recommend that you use MySQL as the DBMS.
            #. Change other setting if needed.
    #. SimTalk
        #. Edit ``.iottalk/conf/simtalk_env`` to meet the requirement.
            #. Set the database configs. The DB use sqlite3 by default. You can use autogen without any changes, but you may lose information when rebuilding or restarting. We recommend that you use MySQL as the DBMS.
            #. Set ``CCM_GUI_URL="http[s]://<your.ccm.public.ip.or.domain>/[ccm/]"`` to correspond to the actual IoTtalk CCM URL.
            #. Set ``CSM_API_URL="http[s]://<your.csm.public.ip.or.domain>/[csm/]"`` to correspond to the actual IoTtalk CSM URL.
            #. Set ``AG_API_URL="http[s]://<your.autogen.public.ip.or.domain>/[autogen/]"`` to correspond to the actual IoTtalk AutoGen Subsystem URL.
            #. Change other setting if needed.

#. db, if you choose MySQL as your DBMS. If not, skip this section:
    #. There is a set of db service setting in ``docker-compose.yml`` named as ``db``.
    #. Edit the ``db`` section of ``docker-compose.yml``.
        #. Set ``MYSQL_ROOT_PASSWORD`` to the desired password
        #. Set ``MYSQL_PASSWORD`` to the desired password
    #. Edit the ``[gui-db]`` section of ``iottalk.ini``.
        #. Set the ``url = <...>`` properly. There are several parts in the url.
            #. The hostname is ``db`` by default.
               It's the name of database service in ``docker-compose.yml``.
               If you don't change the service name, just set it as ``db``.
            #. The ``port`` is ``3306`` by default.
            #. The ``database`` is ``iottalk`` by default.
            #. The corresponding username and password.
            #. An example:
               ``<your-protocol>://<your_username>:<your_pw>@db/iottalk?<other_args>``

#. redis:
    #. Edit the ``[gui-db]`` section of ``iottalk.ini``.
        #. Set ``redis-host = redis`` (to match the service name of redis in
           ``docker-compose.yml``).

#. edutalk:
    #. Generate sample ini config via ``make config``.
    #. ``cp ./edutalk/edutalk.ini.sample ./edutalk/edutalk.ini``
    #. Edit the config file ``./edutalk/edutalk.ini``.
        #. Set Flask secret key ``flask-secret-key = <...>`` as a random generated string
           in the ``[edutalk]`` section.  e.g secret_key = yiyiyi
        #. Set ``userdir = /edutalk`` in the ``[edutalk]`` section,
           please do not change the value.
        #. Set ``web_server_prefix = /edutalk``
        #. Set ``csm_api = http://<public ip>:<external port>/iottalk/csm`` in the
           ``[iottalk]`` section. ::

                e.g csm_api = https://example.edutalk.tw/iottalk/csm

        #. Set ``ccm_api = http://<public ip>:<external port>/iottalk/ccm/api/v0`` in
           the ``[iottalk]`` section. ::

               e.g ccm_api =  https://example.edutalk.tw/iottalk/ccm/api/v0

        #. Set ``ag_url  = http://autogen:8080`` in
           the ``[iottalk]`` section.

        #. Set ``client_id = JzNPCD6uOWuCPZ5hRCNffTfpwmtjE4W3C45wAfv9`` in
           the ``[oauth2]`` section. 

        #. Set ``client_secret = f8OsPyJte3WkQ5qTkLyGWxIhLqlH4s5Q1PzFX665BjMQM5W291ZqzQdNCMMKTSZnJTePO4pLFzxqY11PPqbvHdeUVNS4AcTdlAkK4OfJwyuFUbJT3UwXiNiNBxNB4bBNXTJefbGgA1XKvPWQBGWF7F9wNJUVDhIF`` in the ``[oauth2]`` section. 

        #. Set ``redirect_uri =  https://example.edutalk.tw/edutalk/account/auth/callback`` in
           the ``[oauth2]`` section. 

        #. Set ``discovery_endpoint = https://test.iottalk2.tw/account/.well-known/openid-configuration`` in
           the ``[oauth2]`` section. 

        #. Set ``authorization_endpoint =  https://test.iottalk2.tw/account/oauth2/v1/authorize/`` in
           the ``[oauth2]`` section. 

        #. Set ``token_endpoint = https://test.iottalk2.tw/account/oauth2/v1/token/`` in
           the ``[oauth2]`` section. 

        #. Set ``revocation_endpoint = https://test.iottalk2.tw/account/oauth2/v1/revoke/`` in
           the ``[oauth2]`` section. 

        #. Set ``account_host = https://test.iottalk2.tw/account/`` in
           the ``[oauth2]`` section. 

        #. Set ``admin_username = iottalk`` in
           the ``[edutalk]`` section. (A user on the account system)

        #. Set ``admin_sub = 1`` in
           the ``[edutalk]`` section. (Corresponding user id) 

        #. Set ``admin_email = pcs.nctu@gmail.com`` in
           the ``[edutalk]`` section. (Corresponding email) 

        #. Set ``aaa_api_token = xxxxxxxxxxxxxxxxxx`` in
           the ``[edutalk]`` section. (Corresponding api token) 

        #. Set ``register_need_approve = False`` in
           the ``[edutalk]`` section. 

        #. Modify the value of ``es_password`` to ensure it is the same as ``ELASTIC_PASSWORD`` in ``docker-compose.yml``
           the ``[elasticsearch]`` section. 

    #. Edit the config file ``./iottalk/conf/iottalk.ini``.
        #. Set ``session-timeout = 5256000``.
           Due to the implementation details, please set this value to
           10 years.

Initialize database
----------------------------------------------------------------------
``make initdb``

Start Edutalk
----------------------------------------------------------------------
``make reboot`` 

Add SSL
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

You’ll need SSL if you want to use sensors such as Acceleration,Orientation…
The certbot will autorenew the certificate in this tutorial.

#. Edit the ``[core-mqtt]`` section of ``./iottalk/conf/iottalk.ini``.
    Set ``host = <your.public.ip.or.domain>``

#. Stops containers and removes containers, networks, volumes, and images
    ``docker-compose down``

#. Setting in docker nginx container
    ``docker-compose up -d nginx``

#. Installing Certbot and Obtaining an SSL Certificate
    ``docker exec -it {XXX}_nginx_1 sh`` ::

        # certbot certonly --dry-run --nginx -d eduexample.iottalk.tw --email YOUREMAIL
        # certbot certonly --nginx -d eduexample.iottalk.tw --email YOUREMAIL
        # exit

#. Stops containers
    ``docker-compose down``

#. Set HTTP over TLS
    #. ``./nginx/nginx.conf``
        - Uncomment the line ``include /etc/nginx/conf.d/mqtt.conf;``
    #. ``./nginx/conf.d/iottalk.conf``
        - Uncomment line 8 ~ 12 ::

            server {
                server_name _;
                listen 80 default_server;
                return 301 https://$host$request_uri;
            }

        - Uncomment line 18 ~ 20 ::

            listen 443 ssl;
            include /etc/nginx/conf.d/ssl.conf;
            ssl_session_cache shared:SSL:10m;

    #. ``./nginx/conf.d/ssl.conf``
        - Specify the certificate and private key path if TLS connection is required.
          (Make sure that the certificate and private key are mounted in
          ``docker-compose.yml`` or requested in the container) ::

            ssl_certificate /path/to/certificate;
            ssl_certificate_key /path/to/privkey;

            eg. ssl_certificate /etc/letsencrypt/live/eduexample.iottalk.tw/fullchain.pem;
                ssl_certificate_key /etc/letsencrypt/live/eduexample.iottalk.tw/privkey.pem;
                ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    #. ``./edutalk/edutalk.ini``.
        #. Set ``csm_api = http://<your_domain_name>/iottalk/csm`` in the
           ``[iottalk]`` section. ::

                e.g csm_api = https://eduexample.iottalk.tw/iottalk/csm

        #. Set ``ccm_api = http://<your_domain_name>/iottalk/ccm/api/v0`` in
           the ``[iottalk]`` section. ::

                e.g ccm_api = https://eduexample.iottalk.tw/iottalk/ccm/api/v0

    #. ``./iottalk/conf/iottalk.ini``.
        #. Set ``scheme = wss`` in the ``[core-ws]`` section.
        #. Set ``port = 8884`` in the ``[core-ws]`` section.


Initialize database with fixtures
----------------------------------------------------------------------

After setting up the database related configurations,
please initialize the database with following steps.

::

    make initdb


Debug mode
----------------------------------------------------------------------

#. Modify ``docker-compose.yml``
    #. Edit the ``csm`` section
        #. Set ``command`` = ``iotctl -d -c /iottalk/conf/iottalk.ini start csm``
    #. Edit the ``ccm`` section
        #. Add the following lines in the ``volumes`` ::
            
                - ./iottalk-core:/iottalk-core
                - ./iottalk-classic-gui:/iottalk-ccm
        
        #. Set ``command`` = ::
                
                >
                sh -c 'sleep 3 && 
                        pip install -e /iottalk-core &&
                        pip install -e /iottalk-ccm &&
                        iotctl -d -c /iottalk/conf/iottalk.ini start ccm' 
            
    #. Edit the ``edutalk`` section
        #. Add the following lines in the ``volumes`` ::
            
                - ./edutalk-server:/edutalk-server
                - ./ccmapi-py:/ccmapi
        
        #. Set ``command`` = :: 
                
                >
                sh -c 'pip install --no-cache-dir -e /edutalk-server &&
                        pip install /ccmapi &&
                        yarn --cwd /edutalk-server/edutalk &&
                        edutalk -c /edutalk/edutalk.ini start'
            

#. Modify ``Dockerfile-iottalk`` 
    #. change **`RUN pip install --no-cache-dir /iottalk-core -e /iottalk-ccm`** to **`RUN pip install --no-cache-dir -e /iottalk-core -e /iottalk-ccm`**
    
#. Modify ``./edutalk/edutalk.ini`` 
    #. set ``debug = 1`` in the ``[edutalk]`` section

Launch IoTtalk services
----------------------------------------------------------------------

Via ``docker-compose``::

    docker-compose up

Remove services::

    docker-compose down


Test the setup
----------------------------------------------------------------------

Please visit the ``http://<domain or public ip>`` in the browser
to check the GUI functionality, if the default Nginx setting is used.

The CSM API URL is ``http://<domain or public ip>/csm``.
Please set this URL in your device application for registration.


FAQ
----------------------------------------------------------------------

Q1. ``make`` popped the following error message::

    ssh_exchange_identification: Connection closed by remote host
    fatal: Could not read from remote repository.

    Please make sure you have the correct access rights
    and the repository exists.

A1. During the image building process, the access permission to the
    gitlab repo is required. Please make sure that you have the ssh auth key
    set up for GitLab.

Q2. ``make`` popped the following error message::

    ERROR: Version in "./docker-compose.yml" is unsupported
    ...

A2. This might be caused by using an old version of ``docker-compose`` package.
    Please make sure your ``docker-compose`` is up-to-date.

    In case of Ubuntu 16.04, the version of ``docker-compose`` from the default
    repo is too old.

Q3. How to re-build EduTalk database

A3. Exec the following code

#. Remove services::

    docker-compose down

#. Remove edutalk.db::

    rm ~/docker/edutalk/edutalk.db
    docker-compose down

#. Re-build database::

    make initdb

#. Start services::

    docker-compose up

Dependency upgrade process
----------------------------------------------------------------------

Nginx
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

#. Change the version in the ``config`` target of ``Makefile``.

#. ``make config``

#. Change the version in the ``nginx`` section of ``docker-compose.yml``.

Mosquitto
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

#. Change the version in the ``config`` target of ``Makefile``.

#. ``make config``

#. Change the version in the ``mosquitto`` section of ``docker-compose.yml``.


MariaDB
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

#. Change the tag in the ``docker-compose.yml``

#. Update the version in the instructions of init db section of README.


TODO
----------------------------------------------------------------------

#. Setup docker hub for prebuilt docker image.

#. Nginx SSL configuration and certbot integration.

#. Transform the docker-compose.yml into a template,
   in order to auto-generate MYSQL password and username,
   then init db automatically.

#. Stackable compose file for different usage: https://docs.docker.com/compose/extends/
    - dev setting: mount volume with code
    - mysql / sqlite settings

#. Setup Docker registry to distribute the docker image.
    - maybe setup a new docker hub site
