from time import sleep

from .utils import mkref, sub_wait


def test_invalid_uuid(http_client, mqtt_pub_json):
    """
    Invalid ID should not crash the server.
    """

    mqtt_pub_json('iottalk/api/gui/req/invalid-id', {
        'op': 'attach',
    }, qos=2)
    sleep(1)  # wait for CCM processing


def test_attach(http_client, pub, sub):
    """
    Normal attach
    """
    ref = mkref()

    pub({'op': 'attach', 'ref': ref})
    res = sub_wait(sub)

    assert res.get('op') == 'attach'
    assert res.get('state') == 'ok'
    assert res.get('ref') == ref
