"""Run the source classifier offline with dummy tokens and blocked transport.

Run from the repository root; all arguments are passed to collection_qa.
This wrapper never reads credentials and cannot make provider requests.
"""
import os
import runpy
import sys
from unittest.mock import patch


def forbidden(*args, **kwargs):
    raise AssertionError('Offline classification forbids transport')


if __name__ == '__main__':
    sys.path.insert(0, os.getcwd())
    os.environ['ZENODO_SANDBOX_TOKEN'] = 'offline-fixture-token'
    os.environ['ZENODO_PRODUCTION_TOKEN'] = 'offline-fixture-token'
    sys.argv[0] = 'scripts.collection_qa'
    with patch('requests.sessions.Session.send', forbidden), \
            patch('socket.create_connection', forbidden), \
            patch('socket.socket.connect', forbidden), \
            patch('socket.getaddrinfo', forbidden):
        runpy.run_module('scripts.collection_qa', run_name='__main__')
