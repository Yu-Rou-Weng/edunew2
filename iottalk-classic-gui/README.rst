IoTtalk Classic GUI
================================================================================

*WIP*

The classic web gui for IoTtalk system.

Support python 3.4 and newer.


Installation
--------------------------------------------------------------------------------

IoTtalk classic gui needs port ``7788``.
The Remote_Control needs port ``7789``.

Dependents
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

IoTtalk classic gui is just like its name 'GUI'.
So we needs `mosquitto <https://mosquitto.org/>`_ for communication,
and `IoTtalk-core <https://github.com/IoTtalk/iottalk-core/>`_
for Device controlled.


Requirements
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Most of required packages listed in ``requirements.txt``.
Use the following command to install.

::

    $ pip3 install -r requirements.txt


Config
--------------------------------------------------------------------------------
IoTtalk classic gui use mosquitto websocket, check you installed it.
Add the following line to your mosquitto config file.
We use port ``1884`` for websocket.
You can change it, but make sure the port ``MQTT.websocket_port``
in the `iotgui/config.py` is the same.

#. Set up EC endpoint for the cyber DAs.
    * Go to the configuration file
    * Find the section called ``gui-ec``
    * There is a directive called ``en-endpoint`` in that seciton, fill in the endpoint of EC with this format:
      ``<PROTOCOL>://<HOST>:<PORT>/<PATH>``

      * ``PROTOCOL`` can be either ``http`` or ``https``.
      * If you do not have a proxy service sitting in front of your EC subsystem,
        ``PATH`` **is not required**.
        Also, ``HOST`` and ``PORT`` are the host and the port where your EC subsystem listens.
      * If you have a proxy service sitting in front of your EC subsystem,
        ``PATH`` **may be required** (Check the configuration of your proxy service to find the proper config).
        Also, ``HOST`` and ``PORT`` **are the host and the port where the proxy service listens.**

::

	listener 1884
	protocol websockets

#. Set up Account Subsystem.
    * This section describes the setup steps to connect to the IoTtalk Account Subsystem. If you don't need to use the IoTtalk Account Subsystem, you can skip this section.
    * Go to the configuration file.
    * Find the section call ``gui-oauth2``.
    * From the Account Subsystem, you will get the ``Client ID`` and ``Client Secret``, fill them in the directive called ``client-id`` and ``client-secret`` respectively.
    * In the production version, the IoTtalk server should have an open domain. According to your proxy settings, set the ``redirect-uri`` with the format ``https://<HOST>/<uri-to-gui-root>/auth/callback``.
    * According to the Account Subsystem information, set ``oidc-discovery-endpoint`` to the OpenID Connection discovery endpoint.
    * According to the Account Subsystem information, set ``revocation-endpoint`` to the url for revocation tokens in Account Subsystem, and ``introspect-endpoint`` to the url for introspect tokens. These two endpoints should be found in the OpenID Connection discovery endpoint above.

Start Server
--------------------------------------------------------------------------------

Start ccm(and web) server
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

::

    $ cd iotgui
    $ python3 -m ccm


Start Remote_Control DA
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

::

    $ cd iotgui/da/Remote_control
    $ python3 server.py

