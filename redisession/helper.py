# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import redis
from django.conf import settings


_connections = {}


def get_redis(conf_name='default'):
    """simple helper for getting global Redis connection instances"""
    if conf_name not in _connections:
        _connections[conf_name] = redis.Redis(**getattr(
            settings, 'REDIS_CONFIG', {'default': {}}
        )[conf_name])
    return _connections[conf_name]
