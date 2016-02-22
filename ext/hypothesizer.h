#ifndef STANDARD_KALDI_HYPOTHESIZER_H
#define STANDARD_KALDI_HYPOTHESIZER_H

#include "hypothesis.h"

#include "lat/word-align-lattice.h"

// Hypothesizer reads Kaldi lattices and extracts Hypothesis structs
// with possible transcriptions of the utterances they contain.
class Hypothesizer {
 public:
  Hypothesizer(float frame_shift,
               const kaldi::TransitionModel& transition_model,
               const kaldi::WordBoundaryInfo& word_boundary_info,
               const fst::SymbolTable* word_syms,
               const fst::SymbolTable* phone_syms)
      : frame_shift_(frame_shift),
        transition_model_(&transition_model),
        word_boundary_info_(&word_boundary_info),
        word_syms_(word_syms),
        phone_syms_(phone_syms) {}

  // GetPartial only generates the word sequence for the best
  // hypothesis in the lattice. It doesn't word-align the transcript
  // or anything fancy. It's fast and good for partial results.
  Hypothesis GetPartial(const kaldi::Lattice& lattice);

  // GetFull extracts the best hypothesis in the lattice, pulling
  // out all the stops. It word aligns, phoneme aligns, and generates
  // confidences. It's slower and should only be used when it matters.
  Hypothesis GetFull(const kaldi::Lattice& lattice);

 private:
  float frame_shift_;
  const kaldi::TransitionModel* transition_model_;
  const kaldi::WordBoundaryInfo* word_boundary_info_;
  const fst::SymbolTable* word_syms_;
  const fst::SymbolTable* phone_syms_;
};

#endif  // STANDARD_KALDI_HYPOTHESIZER_H
