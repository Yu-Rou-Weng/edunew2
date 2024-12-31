IoTtalk Core
===============================================================================

.. image:: https://img.shields.io/travis/IoTtalk/iottalk-core/master.svg?style=flat-square
   :alt: Travis CI build status on master branch
   :target: https://travis-ci.org/IoTtalk/iottalk-core

.. image:: https://img.shields.io/badge/GITTER-join%20chat-green.svg?style=flat-square
   :alt: Join the chat at https://gitter.im/ioTtalk/iottalk-core
   :target: https://gitter.im/ioTtalk/iottalk-core?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

.. image:: https://img.shields.io/coveralls/IoTtalk/iottalk-core.svg?branch=master&style=flat-square
   :target: https://coveralls.io/github/IoTtalk/iottalk-core


*WIP*

The core of IoTtalk system.

We support python 2.7, 3.4, 3.5 and 3.6.

.. contents:: Table of Contents


Installation
----------------------------------------------------------------------

Requirements
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Most of them are listed in ``requirements.txt``.
And the rest of them are backport packages.
Please check ``setup.py`` for the backport required.


Development Installation
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

::

    pip install -e.


Command Line Interface Usage
----------------------------------------------------------------------

::

    $ iotctl -h
    usage: iotctl [-h] [-d] [-c INI_PATH] [--version]
                  {initdb,start,stop,restart,status,shell,genconf} ...

    IoTtalk controller

    positional arguments:
      {initdb,start,stop,restart,status,shell,genconf}
                            available sub-commands
        initdb              initialize database
        start               start server
        stop                stop server
        restart             restart server
        status              status server
        shell               start a python interactive shell with db ready
                            enviroment
        genconf             get a copy of sample ini config

    optional arguments:
      -h, --help            show this help message and exit
      -d, --debug           debug mode
      -c INI_PATH, --config INI_PATH
                            IoTtalk ini config file
      --version             show program's version number and exit

Sub-command ``initdb``::

    usage: iotctl initdb [-h] {ccm} ...

    positional arguments:
      {ccm}       available servers
        ccm       init ccm db

    optional arguments:
      -h, --help  show this help message and exit

Sub-command ``start``::

    usage: iotctl start [-h] {csm,ccm,gui} ...

    positional arguments:
      {csm,ccm,gui}  available servers
        csm          start csm server
        ccm          start ccm server
        gui          start gui server

    optional arguments:
      -h, --help     show this help message and exit

Sub-command ``genconf``::

    usage: iotctl genconf [-h] dest

    positional arguments:
      dest        destination path

    optional arguments:
      -h, --help  show this help message and exit


Generate Configuration File
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

::

    $ iotctl genconf /path/to/your/iottalk.ini


Start the Communication Submodule System (CSM) API Server
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

::

    $ iotctl -c /path/to/your/iottalk.ini start csm

If you want to enable the debug mode::

    $ iotctl -d -c /path/to/your/iottalk.ini start csm


Testing
----------------------------------------------------------------------

We use ``pytest`` as test framework and ``tox``.

::

    $ tox -e py36


``pytest`` Fixtures
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

If there is the ``pytest`` fixture which is required by large amount
of test cases, it will be place at ``tests/conftest.py``.
The ``conftest.py`` will be autoloaded by ``pytest``.


Quick Start
----------------------------------------------------------------------

Prerequisite
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

We need to get a MQTT broker listen on ``localhost`` with port 1883.
Currently, the port and address of MQTT broker is not configurable.
Only `Mosquitto <https://mosquitto.org/>`_ tested. The other MQTT 3.1.1
implementation ought to work. We do not use any feature of MQTT v5 draft.
In the following section of this guide, we simply take Mosquitto as example.
It provides some command line tools and helpful for our development.


Installation
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Enter an python virtual envrionment and install this package via ``pip``::

    $ pip install git+https://github.com/IoTtalk/iottalk-core.git@v2.0.0a2

Now, check out the command-line script: ``iotctl``. If you are using ``bash``
or ``tcsh``, please ``rehash`` before issue::

    $ iotctl

Then, it will pop up the usage.


Initialize the Database
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

We only support SQLite, but more DBMS support will be added in future.

::

    $ iotctl initdb

The command ``initdb`` will create an SQLite db in ``$HOME/.iottalk``. Please
check it out, also.


Start the CSM API Server
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

::

    $ iotctl start csm

or, in the debug mode::

    $ iotctl -d start csm

This command will start two daemon threads
(yep, it's thread, no process in this implementation).
One is the http server, the other one is the high privilege api server
(e.g. the api required by the user interface is high privilege).

The http server is bind to localhost with port 9992. And the api server is
listen on specific MQTT topic. We will talk more about the api server at
following device application example.


Try out Simple Device Applications
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

This this section we will try to draw a flow `graph`.
There are IDF(s), IDF function(s), join function(s),
ODF(s) and ODF(s) function in a graph.
Those functions are optional. The minial elements to construct a `graph` is
*an* IDF plus *an* ODF.


Device Application Registration
**************************************************

I will show you the IDF and ODF device applications here.
Assume we have an IDF. It name is ``BetaCat`` and own an IDF ``meow``.
We are going to register it via http api, ``requests`` can do the trick for
us.

Make sure you got ``requests`` isntalled already:

.. code-block:: shell

    $ pip install requests

Then create a new file named ``betacat.py``:


.. code-block:: python

    import requests


    betacat = {
        'name': 'BetaCat',
        'idf_list': [['meow', ['dB']]],
        'accept_protos': ['mqtt'],
        'profile': {
            'model': 'AI',
        },
    }

We have written down the basic profile of `BetaCat`. We missed one thing --
each device application should have a ``id`` which is an ``UUID``.
So, we need to generate one. Just open our python iteractive shell
and get one:

.. code-block:: python

    >>> from uuid import uuid4
    >>> uuid4()
    UUID('df682f01-7c3a-49fd-8f5f-72ce0b6e68c0')

Copy the uuid out and back to our ``betacat.py``:

.. code-block:: python

	betacat_id = 'df682f01-7c3a-49fd-8f5f-72ce0b6e68c0'

And, let's try to register `BetaCat`:

.. code-block:: python

    response = requests.put(
        'http://localhost:9992/{}'.format(betacat_id),
        headers={'Content-Type': 'application/json'},
        json=betacat)

    assert response.status_code == 200

For more info about the http api, please refer to
`here <http://iottalk-spec.readthedocs.io/en/latest/api/res_access/http.html#put-id>`_.

Group up all the snippets:

.. code-block:: python

    import requests

    betacat_id = 'df682f01-7c3a-49fd-8f5f-72ce0b6e68c0'
    betacat = {
        'name': 'BetaCat',
        'idf_list': [['meow', ['dB']]],
        'accept_protos': ['mqtt'],
        'profile': {
            'model': 'AI',
        },
    }

    response = requests.put(
        'http://localhost:9992/{}'.format(betacat_id),
        headers={'Content-Type': 'application/json'},
        json=betacat)

    assert response.status_code == 200

    response = response.json()


Connect to the Control Channels
**************************************************

After registration succes, we have to connect to the MQTT control channel and
let device application wait for
`signals <http://iottalk-spec.readthedocs.io/en/latest/api/res_control/mqtt.html#signals>`_ .

.. code-block:: python

    uplink_topic, downlink_topic = response['ctrl_chans']
    revision = response['rev']  # the token of online/offline msg

And now it's time to connect to MQTT broker. The MQTT protocol implementation
in python we chose is ``paho``:

.. code-block:: python

    import json

    from paho.mqtt.client import Client


    def on_connect(client, userdata, flags, return_code):
        client.publish(
            uplink_topic,
            json.dumps({
                'state': 'online',
                'rev': revision,
            }),
            retain=True)

        client.subscribe(downlink_topic)


    def on_message(client, userdata, msg):
        pass


    client = Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect('localhost', port=1883)
    client.loop_forever()

The behavior and protocol detail have not been revealed in
public documentation, but docstrings and comments in the code base.


Handling the Signals
**************************************************

The signals will be retrieved from the ``downlink_topic`` and handled in the
``on_message`` callback function. In the current stage of iottalk, we only
implemented the ``CONNECT`` and ``DISCONNECT`` signal.

We make ``on_message`` understand ``CONNECT``:

.. code-block:: python

    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode())

        if payload['command'] == 'CONNECT':
            # start our idf data transfer
            # Then, make a response to succes of `CONNECT`
        elif payload['command'] == 'DISCONNECT':
            # stop data transfer

We will show a simple random number generator for demo purpose:

.. code-block:: python

    import random

    from threading import Thread


    def rnd_gen(client, topic):
        while True:
            p = client.publish(topic, int(random.random()*100))
            p.wait_for_publish()


    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode())

        if payload['command'] == 'CONNECT':
            t = Thread(target=rnd_gen, args=(client, payload['topic']))
            t.daemon = True
            t.start()

            # reponse of `CONNECT`
            payload['state'] = 'ok'
            client.publish(uplink_topic, json.dumps(payload))
        elif payload['command'] == 'DISCONNECT':
            pass


The Full Example of Device Application
**************************************************

.. code-block:: python

    import json
    import random

    from threading import Thread

    import requests

    from paho.mqtt.client import Client

    betacat_id = 'df682f01-7c3a-49fd-8f5f-72ce0b6e68c0'
    betacat = {
        'name': 'BetaCat',
        'idf_list': [['meow', ['dB']]],
        'odf_list': [['meow', ['dB']]],
        'accept_protos': ['mqtt'],
        'profile': {
            'model': 'AI',
        },
    }

    response = requests.put(
        'http://localhost:9992/{}'.format(betacat_id),
        headers={'Content-Type': 'application/json'},
        json=betacat)

    assert response.status_code == 200

    response = response.json()

    uplink_topic, downlink_topic = response['ctrl_chans']
    revision = response['rev']  # the token of online/offline msg


    def on_connect(client, userdata, flags, return_code):
        client.publish(
            uplink_topic,
            json.dumps({
                'state': 'online',
                'rev': revision,
            }),
            retain=True)

        client.subscribe(downlink_topic)


    def rnd_gen(client, topic):
        while True:
            p = client.publish(topic, int(random.random()*100))
            p.wait_for_publish()


    def on_message(client, userdata, msg):
        payload = json.loads(msg.payload.decode())

        if payload['command'] == 'CONNECT' and payload.get('idf'):
            t = Thread(target=rnd_gen, args=(client, payload['topic']))
            t.daemon = True
            t.start()

            # reponse of `CONNECT`
            payload['state'] = 'ok'
            client.publish(uplink_topic, json.dumps(payload))
        elif payload['command'] == 'DISCONNECT':
            pass


    client = Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect('localhost', port=1883)
    client.loop_forever()


Example of CSM Graph API Usage
**************************************************

Here is an example to drive our device applications connect to ESM and make
the data path.

If your want to monitor those topic, please try ``mosquitto_sub`` on your
console. It will be helpful for debugging.

.. code-block:: shell

    $ cat api.sh
    #!/bin/sh

    TOPIC='iottalk/api/req/gui/graph/1'
    DA_ID='df682f01-7c3a-49fd-8f5f-72ce0b6e68c0'

    IDF_FUNC='def run(x): return int(x)\n'
    IDF_FUNC_SIG='f87d5c678bdd9e4b1b5f278c29cdf9a0fd01198060d8c6f3a34a6a05ae536e50'

    JOIN_FUNC="def run(x): return x ** 2\n"
    JOIN_FUNC_SIG='70e3d32f1c6abde67d607e3ce77dc286ecf5d0f42fcd18e6336fac5e19a6e07c'


    alias pub="mosquitto_pub -t $TOPIC"

    pub -m '{"op": "attach"}'

    ADD_FUNCS='{"op":"add_funcs","codes":["'$IDF_FUNC'","'$JOIN_FUNC'"], "digests":["'$IDF_FUNC_SIG'", "'$JOIN_FUNC_SIG'"]}'

    echo "$ADD_FUNCS" | pub -l

    pub -m '{"op": "add_link", "da_id": "'$DA_ID'", "idf": "meow", "func": "'$IDF_FUNC_SIG'"}'

    pub -m '{"op": "add_link", "da_id": "'$DA_ID'", "odf": "meow", "func": null}'

    pub -m '{"op": "set_join", "prev": null, "new": "'$JOIN_FUNC_SIG'"}'


Development Notes
----------------------------------------------------------------------

- Use ``qos=2`` in both of pub and sub for control plane.

- In case of MySQL, note that there is a connection timeout setting.
