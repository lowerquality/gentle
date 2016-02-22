#include "decoder.h"

Decoder::Decoder(
    const kaldi::OnlineNnet2FeaturePipelineInfo& info,
    const kaldi::TransitionModel& transition_model,
    const kaldi::OnlineNnet2DecodingConfig& nnet2_decoding_config,
    const kaldi::nnet2::AmNnet& nnet,
    const fst::Fst<fst::StdArc>* decode_fst,
    const kaldi::OnlineIvectorExtractorAdaptationState& adaptation_state)
    : feature_pipeline_(info),
      decoder_(nnet2_decoding_config,
               transition_model,
               nnet,
               *decode_fst,
               &feature_pipeline_),
      silence_weighting_(transition_model, info.silence_weighting_config),
      finalized_(false) {
  this->feature_pipeline_.SetAdaptationState(adaptation_state);
}

void Decoder::AddChunk(kaldi::BaseFloat sampling_rate,
                       const kaldi::VectorBase<kaldi::BaseFloat>& waveform) {
  if (finalized_) {
    return;
  }

  this->feature_pipeline_.AcceptWaveform(sampling_rate, waveform);
  this->AdvanceDecoding();
}

void Decoder::GetAdaptationState(
    kaldi::OnlineIvectorExtractorAdaptationState* adaptation_state) {
  this->feature_pipeline_.GetAdaptationState(adaptation_state);
}

void Decoder::AdvanceDecoding() {
  // Down-weight silence in ivector estimation
  if (this->silence_weighting_.Active()) {
    this->silence_weighting_.ComputeCurrentTraceback(this->decoder_.Decoder());
    this->silence_weighting_.GetDeltaWeights(
        this->feature_pipeline_.NumFramesReady(), &this->delta_weights_);
    this->feature_pipeline_.UpdateFrameWeights(this->delta_weights_);
  }

  this->decoder_.AdvanceDecoding();
}

kaldi::Lattice Decoder::GetBestPath() {
  kaldi::Lattice lattice;

  if (this->decoder_.NumFramesDecoded() == 0) {
    return lattice;
  }

  this->decoder_.GetBestPath(this->finalized_, &lattice);

  return lattice;
}

void Decoder::Finalize() {
  this->finalized_ = true;
  this->feature_pipeline_.InputFinished();
  this->AdvanceDecoding();
  this->decoder_.FinalizeDecoding();
}
