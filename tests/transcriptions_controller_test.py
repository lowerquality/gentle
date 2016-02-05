'''Unit tests for AlignmentsController'''

import unittest
import json

# pylint: disable=no-name-in-module
from nose.tools import assert_equals
from twisted.internet.error import ConnectionDone
from twisted.internet.test.reactormixins import ReactorBuilder
from twisted.python.failure import Failure
from twisted.web.server import NOT_DONE_YET
from twisted.web.test.requesthelper import DummyRequest

from serve import AlignmentsController


class StubAligner(object):
    '''Fake aligner that returns canned respones'''
    def __init__(self, align_stub='', uid_stub='stub-uid'):
        self.align_stub = align_stub
        self.uid_stub = uid_stub
    def next_id(self):
        '''returns canned uid'''
        return self.uid_stub
    # pylint: disable=unused-argument
    def align(self, uid, tran, audio):
        '''returns canned align result'''
        return self.align_stub

# pylint: disable=no-init
class AlignmentsControllerTestsBuilder(ReactorBuilder):
    '''Suite for testing AlignmentsController'''
    def test_async(self):
        '''Test the redirect works when async=true'''
        reactor = self.buildReactor()

        uid = 'myuid'
        want_location = '/alignments/' + uid

        stub_aligner = StubAligner(uid_stub=uid)
        controller = AlignmentsController(stub_aligner, reactor=reactor)

        req = DummyRequest([])
        req.method = 'POST'
        req.args = {'transcript': [''], 'audio': ['']}

        body = controller.render(req)
        assert_equals(body, '')

        assert 'location' in req.outgoingHeaders
        got_location = req.outgoingHeaders['location']

        assert_equals(want_location, got_location)

    def test_sync_cancel(self):
        '''Test that the controller doesn't try to render when the request is cancelled.'''
        reactor = self.buildReactor()

        stub_aligner = StubAligner()
        controller = AlignmentsController(stub_aligner, reactor=reactor)

        req = DummyRequest([])
        req.method = 'POST'
        req.args = {'transcript': [''], 'audio': [''], 'async': ['false']}

        controller.render(req)

        req.processingFailed(
            Failure(ConnectionDone("Simulated disconnect")))

        reactor.callWhenRunning(reactor.stop)
        self.runReactor(reactor)

        assert_equals(req.finished, 0)

    def test_sync(self):
        '''Test the threading/alignment works when async=false'''
        reactor = self.buildReactor()

        expected = {'some': 'result'}

        stub_aligner = StubAligner(align_stub=expected)
        controller = AlignmentsController(stub_aligner, reactor=reactor)

        req = DummyRequest([])
        req.method = 'POST'
        req.args = {'transcript': [''], 'audio': [''], 'async': ['false']}

        finish = req.notifyFinish()
        finish.addCallback(lambda _: reactor.callWhenRunning(reactor.stop))

        body = controller.render(req)
        assert_equals(body, NOT_DONE_YET)

        self.runReactor(reactor, timeout=1)

        assert_equals(len(req.written), 1)
        got = json.loads(req.written[0])
        assert_equals(got, expected)

globals().update(AlignmentsControllerTestsBuilder.makeTestCaseClasses())

if __name__ == '__main__':
    unittest.main()
