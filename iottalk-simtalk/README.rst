SimTalk
=========

File Structure
----------------

- view.py
    - Django View
    
    |
    - SetupView
        - set_parameter()
    
    - ExecutionView
        - set_execution()


- models.py
    - Django Model

- utils.py
    - utility functions

- manage.py
    - view event handler / helpers

- color.py
    - logging color

- static
    - simtalk
        - js
        - css

- template
    - simtalk
        - html files

|

Related Repos
==================

DAI
-----

Install

- installed as python package
- `GitHub IoTtalk v2 Python SDK <https://github.com/IoTtalk/iottalk-py>`_
- file path: ``~/.local/lib/python3.6/site-packages/iottalkpy/dai.py``


AutoGen
----------

Install

- `GitLab AutoGen <https://gitlab.com/IoTtalk/iottalk-autogen>`_


Config

- autogen/config.py
    - need to modify ``ccm_api_url``
    - read ``ccm_api_args``



Pages
========================

Login Page
----------

URL: `/login/<username>`



Setup Page
----------

URL: `/setup/<username>/<p_id>/<do_id>`


Execution Page
--------------

URL: `/execution/<username>/<p_id>`
