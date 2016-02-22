#ifndef STANDARD_KALDI_HYPOTHESIS_H
#define STANDARD_KALDI_HYPOTHESIS_H

#include <string>
#include <vector>

// Phonemes contain information about phoneme timing in the
// transcript. They're included in AlignedWords.
struct Phoneme {
  std::string token;
  double duration;
  bool has_duration;
};

// AlignedWord contains information about the timing of a
// word heard in an audio file.
struct AlignedWord {
  std::string token;
  double start;
  bool has_start;
  double duration;
  bool has_duration;
  std::vector<Phoneme> phones;
};

// A Hypothesis is a possible transcription of an auio file.
// It's the output of this program.
typedef std::vector<AlignedWord> Hypothesis;

std::string MarshalHypothesis(const Hypothesis& hypothesis);

#endif  // STANDARD_KALDI_HYPOTHESIS_H
