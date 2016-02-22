#include "hypothesis.h"

#include <vector>
#include <string>
#include <sstream>

using std::vector;
using std::string;

// MarshalPhones serializes a list of phonemes as JSON
string MarshalPhones(const vector<Phoneme>& phones) {
  std::stringstream ss;

  ss << "[";
  for (int i = 0; i < phones.size(); i++) {
    Phoneme phone = phones[i];
    ss << "{" << std::endl;

    ss << "\"phone\":\"" << phone.token << "\",";
    if (phone.has_duration) {
      ss << "\"duration\":" << phone.duration;
    }

    ss << "}";
    if (i < phones.size() - 1) {
      ss << ",";
    }
  }
  ss << "]";

  return ss.str();
}

// MarshalHypothesis serializes a Hypothesis struct as JSON
std::string MarshalHypothesis(const Hypothesis& hypothesis) {
  std::stringstream ss;

  Hypothesis no_eps;
  for (AlignedWord word : hypothesis) {
    if (word.token == "<eps>") {
      // Don't output anything for <eps> links, which correspond to silence....
      continue;
    }
    no_eps.push_back(word);
  }

  ss << "{\"hypothesis\":";
  ss << "[";

  for (int i = 0; i < no_eps.size(); i++) {
    AlignedWord word = no_eps[i];

    ss << "{";

    ss << "\"word\":\"" << word.token << "\",";
    if (word.has_start) {
      ss << "\"start\":" << word.start << ",";
    }
    if (word.has_duration) {
      ss << "\"duration\":" << word.duration << ",";
    }
    ss << "\"phones\":" << MarshalPhones(word.phones);

    ss << "}";
    if (i < no_eps.size() - 1) {
      ss << ",";
    }
  }

  ss << "]";
  ss << "}" << std::endl;

  return ss.str();
}
