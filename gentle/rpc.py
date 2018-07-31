class RPCProtocol(object):
    '''RPCProtocol is the wire protocol we use to communicate with the
    standard_kaldi subprocess. It's a mixed text/binary protocol
    because we need to send binary audio chunks, but text is simpler.'''

    def __init__(self, send_pipe, recv_pipe):
        '''Initializes the RPCProtocol and reads from recv_pipe until the startup
        message is received.'''
        self.send_pipe = send_pipe
        self.recv_pipe = recv_pipe

        # don't wait for startup
        # body, _ = self._read_reply()
        # if body != 'loaded':
        #     raise RuntimeError('unexpected message from standard_kaldi on load')

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
        MSG_SIZE\n
        METHOD <ARG1> <ARG2> ... <ARGN>\n
        BODY\n
        '''
        data = method
        for arg in args:
            data += ' ' + arg
        data += '\n'
        if body:
            data += body

        try:
            self.send_pipe.write('%d\n' % len(data))
            self.send_pipe.write(data)
            self.send_pipe.write('\n')
        except IOError as _:
            raise IOError("Lost connection with standard_kaldi subprocess")

    def _read_reply(self):
        '''Reads a reply from the stream.
        Reply format:
        MSG_SIZE\n
        STATUS\n
        BODY\n
        '''
        try:
            msg_size = int(self.recv_pipe.readline())
            data = self.recv_pipe.read(msg_size)
            self.recv_pipe.read(1) # trailing newline

            status_str, body = data.split('\n', 1)
            status = int(status_str)
        except IOError as _:
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
