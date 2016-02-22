#ifndef STANDARD_KALDI_RPC_H
#define STANDARD_KALDI_RPC_H

#include <istream>
#include <string>
#include <vector>

// The status codes used by the RPC. Maps to HTTP status codes.
enum {
  STATUS_OK = 200,
  STATUS_BAD_REQUEST = 400,
  STATUS_INTERNAL_SERVER_ERROR = 500
} RPCStatus;

// Read an RPC request. Returns false if the data is malformed.
//
// Methods have this form:
//   MSG_SIZE\n
//   METHOD <ARG1> <ARG2> ... <ARGN>\n
//   BODY\n
bool RPCReadRequest(std::istream& stream,
                    std::string* method,
                    std::vector<std::string>* args,
                    std::vector<char>* body);

// Write the reply part of the RPC.
//
// Replies have this form:
//   MSG_SIZE\n
//   STATUS\n
//   BODY\n
void RPCWriteReply(std::ostream& stream,
                   const int& status,
                   const std::vector<char>& body);

// Write the reply part of the RPC. Same as the above but accepts strings.
void RPCWriteReply(std::ostream& stream,
                   const int& status,
                   const std::string& body_str);

#endif  // STANDARD_KALDI_RPC_H