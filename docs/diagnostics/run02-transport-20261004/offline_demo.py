"""Executable demonstration with blocked sockets/DNS and dummy response only."""
import json
from test_write_observer import ObserverTests

fixture = ObserverTests()
fixture.setUp()
try:
    normal = fixture.run_request(capture_body=True, current_wrappers=True)
    proxy = fixture.run_request(proxy=True, capture_body=True)
    import errno
    failed = fixture.run_request(code=errno.EPIPE, partial=11, capture_body=True)
    print(json.dumps({'network': 'real sockets and DNS blocked',
                      'normal': normal['result'], 'proxy': proxy['result'],
                      'suppressed_partial_write': failed['result'],
                      'response_snapshots': {name: result['capture_artifact'] for name, result in
                          [('normal', normal), ('proxy', proxy), ('suppressed_partial_write', failed)]}}, indent=2))
finally:
    fixture.doCleanups()
