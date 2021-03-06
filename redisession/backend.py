# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import struct
import time
from importlib import import_module

import redis
from django.conf import settings
from django.contrib.sessions.backends.base import CreateError, SessionBase

try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:
    import pickle


logger = logging.getLogger('redisession')


conf = {
    'SERVER': {},
    'USE_HASH': True,
    'KEY_GENERATOR': lambda x: x.decode('hex'),
    'HASH_KEY_GENERATOR': lambda x: x[:4].decode('hex'),
    'HASH_KEYS_CHECK_FOR_EXPIRY':
    lambda r: (reduce(
        lambda p, y: p.randomkey(), xrange(100), r.pipeline()).execute()),
    'COMPRESS_LIB': 'snappy',
    'COMPRESS_MIN_LENGTH': 400,
    'LOG_KEY_ERROR': False
}
conf.update(getattr(settings, 'REDIS_SESSION_CONFIG', {}))


if isinstance(conf['SERVER'], dict):

    class GetRedis(object):

        def __call__(self, conf):
            if not hasattr(self, '_redis'):
                self._redis = redis.Redis(**conf)
            return self._redis

    get_redis = GetRedis()

else:
    from redisession.helper import get_redis


if conf['COMPRESS_LIB']:
    compress_lib = import_module(conf['COMPRESS_LIB'])


FLAG_COMPRESSED = 1


class SessionStore(SessionBase):

    def __init__(self, session_key=None):
        self._redis = get_redis(conf['SERVER'])
        super(SessionStore, self).__init__(session_key)

        if not hasattr(self, 'serializer'):
            self.serializer = lambda: pickle

    def encode(self, session_dict):
        data = self.serializer().dumps(session_dict)
        flag = 0
        if conf['COMPRESS_LIB'] and len(data) >= conf['COMPRESS_MIN_LENGTH']:
            compressed = compress_lib.compress(data)
            if len(compressed) < len(data):
                flag |= FLAG_COMPRESSED
                data = compressed
        return chr(flag) + data

    def decode(self, session_data):
        flag, data = ord(session_data[:1]), session_data[1:]
        if flag & FLAG_COMPRESSED:
            if conf['COMPRESS_LIB']:
                return self.serializer().loads(compress_lib.decompress(data))
            raise ValueError('redisession: found compressed data without '
                             'COMPRESS_LIB specified.')
        return self.serializer().loads(data)

    def create(self):
        for i in xrange(10000):
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return
        raise RuntimeError('Unable to create a new session key.')

    if conf['USE_HASH']:
        def _make_key(self, session_key):
            try:
                return (
                    conf['HASH_KEY_GENERATOR'](session_key),
                    conf['KEY_GENERATOR'](session_key)
                )
            except Exception:
                if conf['LOG_KEY_ERROR']:
                    logger.warning(
                        'misconfigured key-generator or bad key "{}"'.format(
                            session_key
                        )
                    )

        def save(self, must_create=False):
            if must_create:
                func = self._redis.hsetnx
            else:
                func = self._redis.hset
            session_data = self.encode(self._get_session(no_load=must_create))
            expire_date = struct.pack(
                '>I', int(time.time() + self.get_expiry_age()))
            key = self._make_key(self._get_or_create_session_key())
            if key is None:
                raise CreateError
            result = func(*key, value=expire_date + session_data)
            if must_create and not result:
                raise CreateError

        def load(self):
            key = self._make_key(self._get_or_create_session_key())
            if key is not None:
                session_data = self._redis.hget(*key)
                if session_data is not None:
                    expire_date = struct.unpack('>I', session_data[:4])[0]
                    if expire_date > time.time():
                        return self.decode(session_data[4:])
            self.create()
            return {}

        def exists(self, session_key):
            key = self._make_key(session_key)
            if key is not None:
                return self._redis.hexists(*key)
            return False

        def delete(self, session_key=None):
            if session_key is None:
                if self.session_key is None:
                    return
                session_key = self.session_key
            key = self._make_key(session_key)
            if key is not None:
                self._redis.hdel(*key)

    else:  # not conf['USE_HASH']
        def _make_key(self, session_key):
            try:
                return conf['KEY_GENERATOR'](session_key)
            except Exception:
                if conf['LOG_KEY_ERROR']:
                    logger.warning(
                        'misconfigured key-generator or bad key "{}"'.format(
                            session_key
                        )
                    )

        def save(self, must_create=False):
            pipe = self._redis.pipeline()
            if must_create:
                pipe = pipe.setnx
            else:
                pipe = pipe.set
            session_data = self.encode(self._get_session(no_load=must_create))
            key = self._make_key(self._get_or_create_session_key())
            if key is None:
                raise CreateError
            result = pipe(key, session_data).expire(
                key, self.get_expiry_age()
            ).execute()

            # for Python 2.4 (Django 1.3)
            if must_create and not (result[0] and result[1]):
                raise CreateError

        def load(self):
            key = self._make_key(self._get_or_create_session_key())
            if key is not None:
                session_data = self._redis.get(key)
                if session_data is not None:
                    return self.decode(session_data)
            self.create()
            return {}

        def exists(self, session_key):
            key = self._make_key(session_key)
            if key is not None:
                return key in self._redis
            return False

        def delete(self, session_key=None):
            if session_key is None:
                if self.session_key is None:
                    return
                session_key = self.session_key
            key = self._make_key(session_key)
            if key is not None:
                self._redis.delete(key)
