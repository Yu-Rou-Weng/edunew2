# shared context

from redis import StrictRedis

from iotgui import config

redis = StrictRedis(config.REDIS_HOST, config.REDIS_PORT)
