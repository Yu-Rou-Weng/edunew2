import logging

log = logging.getLogger('iottalk.csm')


class BaseAPIHandler(object):
    def __init__(self, req, res, res_topic=None, req_topic=None, id_=None,
                 pub_func=None, destroy_cb=None):
        '''
        :param req: the subscribe function for request. It must have a function
            attribute ``remove_callback`` for destruction.
        :param res: the publish function for response.
        :param res_topic: optional. response topic in ``str``.
        :param req_topic: optional. request topic in ``str``.
        :param id_: optional
        :param pub_func: optional.
            A publish function without preconfigured topic.
            Useful for Graph to handle delayed response.
            Function signature: ``f(topic, message)``
        :param destroy_cb: the cleanup callback. usually call on ``detach``.
        '''
        self.req = req
        self.res = res
        if res_topic is not None:
            self.res_topic = res_topic
        if req_topic is not None:
            self.req_topic = req_topic
        if id_ is not None:
            self.id = id_
        if pub_func is not None:
            self.pub_func = pub_func

        self.destroy_cb = destroy_cb

        self.req(self.on_req)

    def detach(self):
        self.req.remove_callback()

        if self.destroy_cb:
            self.destroy_cb()
        log.debug('API handler %r detach', self)

    def on_req(self, client, userdata, msg):
        raise NotImplementedError()

    def __del__(self):
        log.debug('API handler %r destroy', self)

    def unknown_op(self, payload, opcode):
        msg = 'unknown op: `{}`'.format(opcode)
        log.warning(msg)
        return self.send_error(payload, reason=msg)
