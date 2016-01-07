#include "rpc.h"

#include <sstream>
#include <iostream>

using std::vector;
using std::string;

// Parse the method part of an RPC request. Returns false if the data is
// malformed.
//
// Methods have this form:
//   METHOD <ARG1> <ARG2> ... <ARGN>\n
bool RPCReadMethod(std::istream& stream, string* method, vector<string>* args) {
  std::string line;
  if (!std::getline(stream, line)) {
    return false;
  }
  std::stringstream ss(line);

  if (!(ss >> *method)) {
    return false;
  }

  string buf;
  while (ss >> buf) {
    args->push_back(buf);
  }

  return true;
}

class membuf : public std::basic_streambuf<char> {
 public:
  membuf(std::vector<char>& vec) {
    setg(vec.data(), vec.data(), vec.data() + vec.size());
  }
};

bool RPCReadRequest(std::istream& stream,
                    string* method,
                    vector<string>* args,
                    vector<char>* body) {
  string size_line;
  if (!std::getline(stream, size_line)) {
    std::cerr << "get size line" << std::endl;
    return false;
  }

  std::stringstream size_ss(size_line);
  size_t size;
  if (!(size_ss >> size)) {
    std::cerr << "get size" << std::endl;
    return false;
  }

  vector<char> request_bytes(size);
  if (!stream.read(&request_bytes[0], size)) {
    std::cerr << "read" << std::endl;
    return false;
  }
  char trailing_newline;
  if (!stream.read(&trailing_newline, 1)) {
    std::cerr << "get newline" << std::endl;
    return false;
  }
  if (trailing_newline != '\n') {
    std::cerr << "bad trailing newline" << std::endl;
    return false;
  }

  membuf request_buf(request_bytes);
  std::istream request_stream(&request_buf);

  if (!RPCReadMethod(request_stream, method, args)) {
    std::cerr << "read method" << std::endl;
    return false;
  }

  // Read the rest into the body
  body->insert(body->begin(), std::istreambuf_iterator<char>(request_stream),
               {});

  return true;
}

// Write the reply part of the RPC.
//
// Replies have this form:
//   MSG_SIZE\n
//   STATUS\n
//   BODY\n
void RPCWriteReply(std::ostream& stream,
                   const int& status,
                   const vector<char>& body) {
  std::stringstream ss;
  ss << status << std::endl;
  ss.write(&body[0], body.size());
  const string& reply_str = ss.str();

  stream << reply_str.size() << std::endl;
  stream.write(&reply_str[0], reply_str.size());
  stream << std::endl;
}

void RPCWriteReply(std::ostream& stream,
                   const int& status,
                   const string& body_str) {
  vector<char> body(body_str.begin(), body_str.end());
  RPCWriteReply(stream, status, body);
}
