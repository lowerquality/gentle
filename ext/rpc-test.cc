#include "rpc.h"

#include <sstream>
#include <string>

#include "base/kaldi-common.h"

using std::string;
using std::stringstream;
using std::vector;

std::string TestReadRequest(std::istream& stream,
                            const bool& want_return,
                            const string& want_method,
                            const vector<string>& want_args,
                            const vector<char>& want_body) {
  string got_method;
  vector<string> got_args;
  vector<char> got_body;
  bool got_return = RPCReadRequest(stream, &got_method, &got_args, &got_body);
  if (got_return != want_return) {
    return "got_return != want_return";
  }
  if (got_args.size() != want_args.size()) {
    return "got_args.size() != want_args.size()";
  }
  for (int i = 0; i < got_args.size(); i++) {
    if (got_args[i] != want_args[i]) {
      return "got_args[i] != want_args[i]";
    }
  }
  string got_body_str(&got_body[0], got_body.size());
  if (got_body.size() != want_body.size()) {
    return "got_body.size() != want_body.size()";
  }
  for (int i = 0; i < got_body.size(); i++) {
    if (got_body[i] != want_body[i]) {
      return "got_body[i] != want_body[i]";
    }
  }
  return "";
}

vector<char> Bytes(const string& str) {
  return vector<char>(str.begin(), str.end());
}

void Report(const string& name, const string& err) {
  if (err == "") {
    return;
  }
  std::cerr << "FAIL: " << name << ": " << err << std::endl;
}

void ReadRequestTests() {
  stringstream valid("15\nmethod arg\nbody\n");
  Report("valid",
         TestReadRequest(valid, true, "method", {"arg"}, Bytes("body")));
  stringstream no_args("11\nmethod\nbody\n");
  Report("no args", TestReadRequest(valid, true, "method", {}, Bytes("body")));
  stringstream no_body("11\nmethod arg\n\n");
  Report("no body", TestReadRequest(no_body, true, "method", {"arg"}, {}));
  stringstream missing_newline("15\nmethod arg\nbody");
  Report("missing newline",
         TestReadRequest(missing_newline, false, "", {}, {}));
  stringstream undeflow("11\nmethod arg\nbody\n");
  Report("underflow", TestReadRequest(undeflow, false, "", {}, {}));
  stringstream overflow("99\nmethod arg\nbody\n");
  Report("overflow", TestReadRequest(overflow, false, "", {}, {}));
  stringstream bad_size("not int 11\nmethod arg\nbody\n");
  Report("bad size", TestReadRequest(bad_size, false, "", {}, {}));
  stringstream no_method("6\n \nbody\n");
  Report("no method", TestReadRequest(no_method, false, "", {}, {}));
  stringstream empty("");
  Report("empty", TestReadRequest(empty, false, "", {}, {}));
  stringstream newline_body("19\nmethod\nwith\nnewline\n");
  Report("newline body", TestReadRequest(newline_body, true, "method", {},
                                         Bytes("with\nnewline")));

  vector<char> with_null({'5', '\n', 'm', '\n', 'a', '\0', 'b', '\n'});
  stringstream with_null_stream(&with_null[0], with_null.size());
  Report("with null in body",
         TestReadRequest(with_null_stream, true, "m", {}, {'a', '\0', 'b'}));
}

int main() {
  ReadRequestTests();
}