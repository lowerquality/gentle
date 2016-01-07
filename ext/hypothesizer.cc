#include "hypothesizer.h"

#include "lat/lattice-functions.h"

Hypothesis Hypothesizer::GetPartial(const kaldi::Lattice& lattice) {
  Hypothesis hyp;

  // Let's see what words are in here..
  std::vector<int32> words;
  std::vector<int32> alignment;
  kaldi::LatticeWeight weight;
  GetLinearSymbolSequence(lattice, &alignment, &words, &weight);

  for (int32 word : words) {
    AlignedWord aligned;
    aligned.token = this->word_syms_->Find(word);
    hyp.push_back(aligned);
  }

  return hyp;
}

Hypothesis Hypothesizer::GetFull(const kaldi::Lattice& lattice) {
  Hypothesis hyp;

  kaldi::CompactLattice clat;
  ConvertLattice(lattice, &clat);

  // Compute prons alignment (see: kaldi/latbin/nbest-to-prons.cc)
  kaldi::CompactLattice aligned_clat;

  std::vector<int32> words, times, lengths;
  std::vector<std::vector<int32> > prons;
  std::vector<std::vector<int32> > phone_lengths;

  WordAlignLattice(clat, *this->transition_model_, *this->word_boundary_info_,
                   0, &aligned_clat);

  CompactLatticeToWordProns(*this->transition_model_, clat, &words, &times,
                            &lengths, &prons, &phone_lengths);

  for (int i = 0; i < words.size(); i++) {
    AlignedWord aligned;
    aligned.token = this->word_syms_->Find(words[i]);
    aligned.start = times[i] * this->frame_shift_;
    aligned.has_start = true;
    aligned.duration = lengths[i] * this->frame_shift_;
    aligned.has_duration = true;

    for (size_t j = 0; j < phone_lengths[i].size(); j++) {
      Phoneme phone;
      phone.token = this->phone_syms_->Find(prons[i][j]);
      phone.duration = phone_lengths[i][j] * this->frame_shift_;
      phone.has_duration = true;
      aligned.phones.push_back(phone);
    }

    hyp.push_back(aligned);
  }

  return hyp;
}
