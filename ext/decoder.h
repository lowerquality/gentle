#ifndef STANDARD_KALDI_DECODER_H
#define STANDARD_KALDI_DECODER_H

#include "online2/online-nnet2-decoding.h"

// Decoder represents an in-progress transcription of an utterance.
class Decoder {
 public:
  Decoder(const kaldi::OnlineNnet2FeaturePipelineInfo& info,
          const kaldi::TransitionModel& transition_model,
          const kaldi::OnlineNnet2DecodingConfig& nnet2_decoding_config,
          const kaldi::nnet2::AmNnet& nnet,
          const fst::Fst<fst::StdArc>* decode_fst,
          const kaldi::OnlineIvectorExtractorAdaptationState& adaptation_state);

  // AddChunk adds an audio chunk of audio to the decoding pipeline.
  void AddChunk(kaldi::BaseFloat sampling_rate,
                const kaldi::VectorBase<kaldi::BaseFloat>& waveform);
  // GetAdaptationState gets the ivector extractor's adaptation state
  void GetAdaptationState(
      kaldi::OnlineIvectorExtractorAdaptationState* adaptation_state);
  // GetBestPath outputs the decoder's current one-best lattice.
  kaldi::Lattice GetBestPath();
  // Finalize is called when you're finished adding chunks. It flushes the
  // data pipeline and cleans up the lattice. After calling Finalize all
  // calls to AddChunk will fail.
  void Finalize();

 private:
  // AdvanceDecoding processes any chunks in the decoding pipeline,
  // applying silence weighting.
  void AdvanceDecoding();

  kaldi::OnlineNnet2FeaturePipeline feature_pipeline_;
  kaldi::SingleUtteranceNnet2Decoder decoder_;

  kaldi::OnlineSilenceWeighting silence_weighting_;
  std::vector<std::pair<int32, kaldi::BaseFloat> > delta_weights_;

  bool finalized_;
};

#endif  // STANDARD_KALDI_DECODER_H
