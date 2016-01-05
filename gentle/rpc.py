class RPCProtocol(object):
    '''RPCProtocol is the wire protocol we use to communicate with the
    standard_kaldi subprocess. It's a mixed text/binary protocol
    because we need to send binary audio chunks, but text is simpler.'''

    def __init__(self, send_pipe, recv_pipe):
        '''Initializes the RPCProtocol and reads from recv_pipe until the startup
        message is received.'''
        self.send_pipe = send_pipe
        self.recv_pipe = recv_pipe

        # wait for startup
        body, _ = self._read_reply()
        if body != 'loaded':
            raise RuntimeError('unexpected message from standard_kaldi on load')

    def do(self, method, *args, **kwargs):
        '''Performs the method requested and returns the response body.
        The body keyword argument can be used to provide a binary request
        body. Throws an RPCError when the RPC returns an error.'''
        body = kwargs.get('body', None)
        self._write_request(method, args, body)
        return self._read_reply()

    def _write_request(self, method, args, body):
        '''Writes a request to the stream.
        Request format:
        METHOD <ARG1> <ARG2> ... <ARGN>\n
        BODY_SIZE\n
        BODY\n
        '''
        args_string = ' '.join(args)

        try:
            self.send_pipe.write('%s %s\n' % (method, args_string))
            if body:
                self.send_pipe.write('%d\n' % len(body))
                self.send_pipe.write(body)
            else:
                self.send_pipe.write('0\n')
            self.send_pipe.write('\n')
        except IOError, _:
            raise IOError("Lost connection with standard_kaldi subprocess")

    def _read_reply(self):
        '''Reads a reply from the stream.
        Reply format:
        STATUS\n
        BODY_SIZE\n
        BODY\n
        '''
        try:
            status = int(self.recv_pipe.readline())
            body_size = int(self.recv_pipe.readline())
            body = self.recv_pipe.read(body_size)
            self.recv_pipe.read(1) # trailing newline
        except IOError, _:
            raise IOError("Lost connection with standard_kaldi subprocess")

        if status < 200 or status >= 300:
            raise RPCError(status, body)

        return body, status

class RPCError(Exception):
    '''Error thrown when standard_kaldi returns an error (in-band)'''
    def __init__(self, status, why):
        self.status = status
        self.why = why
    def __str__(self):
        return 'standard_kaldi: error %d: %s' % (self.status, self.why)
