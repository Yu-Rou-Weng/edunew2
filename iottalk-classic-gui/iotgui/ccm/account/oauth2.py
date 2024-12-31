import logging
import datetime

from authlib.integrations.requests_client import OAuth2Session
from requests import exceptions as requests_exceptions

from iotgui import config, db
from iotgui.db import model

log = logging.getLogger("{}ccm.auth\033[0m".format(config.LOG_COLOR_GUI))

# Create an OAuth 2.0 client provided Authlib
#
# Ref: https://tinyurl.com/2rs2594h (OAuth2Session documentation)
oauth2_client = OAuth2Session(
    client_id=config.OAUTH2_CLIENT_ID,
    client_secret=config.OAUTH2_CLIENT_SECRET,
    revocation_endpoint_auth_method='client_secret_basic'
)


def auth(sub, db_session) -> model.User or None:
    """
    Authenticate user through OAuth sub.

    This procedure will check user sub is exist or not.
    Sometimes the user access token is valid,
    but there is no record in iottalk,
    which will cause subsequent query errors.

    :param sub: The user sub from Account Subsystem.
    :type sub: string.

    :return: model.User or None.
    """
    return (
        db_session.query(model.User)
                  .filter(model.User.sub == sub)
                  .first())


def introspect_token(token, type):
    """
    Intorspect Tokens.

    This procedure will check whether the token is valid.
    Only return sub if the token is valid, active and not expired.
    Because the GUI server is a resource server, the user may not have used the GUI before.
    So sub may not be in the IoTtalk Classic GUI DB.

    :param token: The Token that requires introspection.
    :type token: string.

    :return: The dictionary result of the Account Subsystem responds.
             Includes sub, proFerent_username, email, etc.
    """
    response = oauth2_client.introspect_token(
        config.OAUTH2_INTROSPECT_ENDPOINT,
        token=token,
        token_type_hint=type)

    # Check the HTTP request status.
    if response.status_code // 100 != 2:
        return None

    result = response.json()

    # Check the token is still active.
    if result.get('active') is False:
        return None

    # Check the token is not expired.
    if result.get('exp') < datetime.datetime.now().timestamp():
        return None

    return result


def introspect_access_token(token):
    """
    Intorspect Access Tokens.

    Reference introspect_access_token.

    :param token: The Access Token that requires introspection.
    :type token: string.

    :return: string for sub or None.
    """
    return introspect_token(token, 'access_token')


def introspect_refresh_token(token):
    """
    Intorspect Refresh Tokens.

    Reference introspect_access_token.

    :param token: The Refresh Token that requires introspection.
    :type token: string.

    :return: string for sub or None.
    """
    return introspect_token(token, 'refresh_token')


def revoke_access_token(http_session):
    """
    Revoke the access token.

    This procedure will check if the Access Token belongs to IoTtalk classic GUI.
    If not, this procedure will skip the revocation process to avoid
    revoking other system Access Tokens.
    """
    db_session = db.get_session()
    # check access token
    access_token_record = \
        (db_session
            .query(model.AccessToken)
            .filter_by(id=http_session.pop('access_token_id', 0))
            .first()
         )

    if access_token_record:
        try:
            # Revoke the access token
            response = oauth2_client.revoke_token(
                config.OAUTH2_REVOCATION_ENDPOINT,
                token=access_token_record.token,
                token_type_hint='access_token'
            )
            response.raise_for_status()
        except requests_exceptions.Timeout:
            log.warning('Revoke an access token failed due to request timeout')
        except requests_exceptions.TooManyRedirects:
            log.warning('Revoke an access token failed due to too many redirects')
        except (requests_exceptions.HTTPError,
                requests_exceptions.RequestException) as e:
            log.warning('Revoke an access token failed, %s', e)
        finally:
            # Delete the access token record no matter whether access token
            # revocation is success or not
            db_session.delete(access_token_record)
            db_session.commit()

    db_session.close()
