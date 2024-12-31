IoTtalk AutoGen Subsystem
=========================

Requirement
-----------

We recommend using Python >= 3.7 (for numpy), and you should use **pip >= 10.0.0**

Installation
------------
Install required system library::

    sudo apt-get install libmysqlclient-dev


Install required package::

    pip install -r requirements.txt

Copy environment file from example::

    cp _/env/.env.example _/env/env

Modify environment file `_/env/env`, replace any **`<xxx>`** to your setting

    #. Set up the SECRET_KEY::

        SECRET_KEY="<your_secret_key>"

    #. Set up the ccm host to your iottalk-ccm server::

        CCM_API_URL = 'http://<CCM_HOST>[:<CCM_PORT>]/api/v0'

    #. Set up other environments to be changed

Migrate database::

    ./manage.py migratesites

Run the server::

    ./manage.py runsites -s autogen

Create Example XTalk
--------------------

#. Create a Django application ``footalk``::

    ./manage.py startapp footalk

#. Create ``footalk/settings.py`` for it as following::

    import os

    from .settings import *

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    SECRET_KEY = 'my_very_secret_code'

    INSTALLED_APPS += [
        'footalk.apps.FootalkConfig',
    ]

    ROOT_URLCONF = 'footalk.urls'

    AG_API_URL = 'http://localhost:8080'

#. Install the settings file in the dir ``_``::

    cd _ && ln -s ../footalk/settings.py footalk_settings.py

#. Create ``footalk/urls.py`` for it as following::

    from django.urls import path

    from . import views

    urlpatterns = [
        path('', views.index, name='index'),
    ]

#. Modify your ``footalk/views.py`` and create a view function ``index``::

    def index(request):
        ...

#. Migrate DB::

    ./manage.py makemigrations --settings=_.footalk_settings
    ./manage.py migrate --settings=_.footalk_settings

#. Start your FooTalk at port 8081 and the AutoGen Subsystem at port 8080::

    ./manage.py runsites -s autogen:8080 -s footalk:8081
