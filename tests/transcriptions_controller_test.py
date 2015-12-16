'''Unit tests for TranscriptionsController'''

import unittest
import json

# pylint: disable=no-name-in-module
from nose.tools import assert_equals
from twisted.internet.error import ConnectionDone
from twisted.internet.test.reactormixins import ReactorBuilder
from twisted.python.failure import Failure
from twisted.web.server import NOT_DONE_YET
from twisted.web.test.requesthelper import DummyRequest

from serve import TranscriptionsController


class StubTranscriber(object):
    '''Fake transcriber that returns canned respones'''
    def __init__(self, transcribe_stub='', uid_stub='stub-uid'):
        self.transcribe_stub = transcribe_stub
        self.uid_stub = uid_stub
    def next_id(self):
        '''returns canned uid'''
        return self.uid_stub
    # pylint: disable=unused-argument
    def transcribe(self, uid, tran, audio):
        '''returns canned transcribe result'''
        return self.transcribe_stub

# pylint: disable=no-init
class TranscriptionsControllerTestsBuilder(ReactorBuilder):
    '''Suite for testing TranscriptionsController'''
    def test_async(self):
        '''Test the redirect works when async=true'''
        reactor = self.buildReactor()

        uid = 'myuid'
        want_location = '/transcriptions/' + uid

        stub_transcriber = StubTranscriber(uid_stub=uid)
        controller = TranscriptionsController(stub_transcriber, reactor=reactor)

        req = DummyRequest([])
        req.method = 'POST'
        req.args = {'transcript': [''], 'audio': ['']}

        body = controller.render(req)
        assert_equals(body, None)

        assert 'location' in req.outgoingHeaders
        got_location = req.outgoingHeaders['location']

        assert_equals(want_location, got_location)

    def test_sync_cancel(self):
        '''Test that the controller doesn't try to render when the request is cancelled.'''
        reactor = self.buildReactor()

        stub_transcriber = StubTranscriber()
        controller = TranscriptionsController(stub_transcriber, reactor=reactor)

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
        '''Test the threading/transcription works when async=false'''
        reactor = self.buildReactor()

        expected = {'some': 'result'}

        stub_transcriber = StubTranscriber(transcribe_stub=expected)
        controller = TranscriptionsController(stub_transcriber, reactor=reactor)

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

globals().update(TranscriptionsControllerTestsBuilder.makeTestCaseClasses())

if __name__ == '__main__':
    unittest.main()
