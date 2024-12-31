from types import SimpleNamespace

from iotgui.cli import (
    load_config,
    load_flask_config,
)


def get_application(*args, **kwargs):
    # Load configurations from a configuration file.
    # SimpleNamespace allows you to create an instance with attribute access to its
    # namespace. We use this to mimic the Namespace object returned after using argparse
    # library to parse cli arguments.
    #
    # Ref: https://stackoverflow.com/a/28345836/8997651
    # Ref: https://docs.python.org/3/library/types.html#types.SimpleNamespace
    load_config(SimpleNamespace(**kwargs))

    # Load flask app after the population of the specified configurations,
    # otherwise some code will adopt default options, which may cause some issues.
    from iotgui.ccm.server import app as flask_app

    # Load flask configurations
    load_flask_config(flask_app)

    return flask_app
