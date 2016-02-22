// Escape hatch from Kaldi.
//
// Use standard in/out trickery to get control flow into other languages.

// Based on online2-wav-nnet2-latgen-faster

#include <stdlib.h>

#include "online2/online-nnet2-decoding.h"
#include "online2/onlinebin-util.h"
#include "online2/online-timing.h"
#include "online2/online-endpoint.h"
#include "fstext/fstext-lib.h"
#include "lat/lattice-functions.h"
#include "lat/word-align-lattice.h"
#include "hmm/hmm-utils.h"
#include "thread/kaldi-thread.h"

#include "decoder.h"
#include "hypothesis.h"
#include "hypothesizer.h"
#include "rpc.h"

const int arate = 8000;

void ConfigFeatureInfo(kaldi::OnlineNnet2FeaturePipelineInfo& info,
                       std::string ivector_model_dir) {
  // online_nnet2_decoding.conf
  info.feature_type = "mfcc";

  // ivector_extractor.conf
  info.use_ivectors = true;
  ReadKaldiObject(ivector_model_dir + "/final.mat",
                  &info.ivector_extractor_info.lda_mat);
  ReadKaldiObject(ivector_model_dir + "/global_cmvn.stats",
                  &info.ivector_extractor_info.global_cmvn_stats);
  ReadKaldiObject(ivector_model_dir + "/final.dubm",
                  &info.ivector_extractor_info.diag_ubm);
  ReadKaldiObject(ivector_model_dir + "/final.ie",
                  &info.ivector_extractor_info.extractor);
  info.ivector_extractor_info.greedy_ivector_extractor = true;
  info.ivector_extractor_info.ivector_period = 10;
  info.ivector_extractor_info.max_count = 0.0;
  info.ivector_extractor_info.max_remembered_frames = 1000;
  info.ivector_extractor_info.min_post = 0.025;
  info.ivector_extractor_info.num_cg_iters = 15;
  info.ivector_extractor_info.num_gselect = 5;
  info.ivector_extractor_info.posterior_scale = 0.1;
  info.ivector_extractor_info.use_most_recent_ivector = true;

  // splice.conf
  info.ivector_extractor_info.splice_opts.left_context = 3;
  info.ivector_extractor_info.splice_opts.right_context = 3;

  // mfcc.conf
  info.mfcc_opts.frame_opts.samp_freq = arate;
  info.mfcc_opts.use_energy = false;

  info.ivector_extractor_info.Check();
}

void ConfigDecoding(kaldi::OnlineNnet2DecodingConfig& config) {
  config.decodable_opts.acoustic_scale = 0.1;
  config.decoder_opts.lattice_beam = 6.0;
  config.decoder_opts.beam = 15.0;
  config.decoder_opts.max_active = 7000;
}

void ConfigEndpoint(kaldi::OnlineEndpointConfig& config) {
  config.silence_phones = "1:2:3:4:5:6:7:8:9:10:11:12:13:14:15:16:17:18:19:20";
}

void usage() {
  fprintf(stderr, "usage: standard_kaldi nnet_dir hclg_path proto_lang_dir\n");
}

int main(int argc, char* argv[]) {
  using namespace kaldi;
  using namespace fst;

  if (argc != 4) {
    usage();
    return EXIT_FAILURE;
  }

  const string nnet_dir = argv[1];
  const string fst_rxfilename = argv[2];
  const string proto_lang_dir = argv[3];

  const string ivector_model_dir = nnet_dir + "/ivector_extractor";
  const string nnet2_rxfilename = proto_lang_dir + "/modeldir/final.mdl";
  const string word_syms_rxfilename = proto_lang_dir + "/langdir/words.txt";
  const string phone_syms_rxfilename = proto_lang_dir + "/langdir/phones.txt";
  const string word_boundary_filename =
      proto_lang_dir + "/langdir/phones/word_boundary.int";

  setbuf(stdout, NULL);

  std::cerr << "Loading...\n";

  OnlineNnet2FeaturePipelineInfo feature_info;
  ConfigFeatureInfo(feature_info, ivector_model_dir);
  OnlineNnet2DecodingConfig nnet2_decoding_config;
  ConfigDecoding(nnet2_decoding_config);
  OnlineEndpointConfig endpoint_config;
  ConfigEndpoint(endpoint_config);

  WordBoundaryInfoNewOpts opts;  // use default opts
  WordBoundaryInfo word_boundary_info(opts, word_boundary_filename);

  BaseFloat frame_shift = feature_info.FrameShiftInSeconds();
  fprintf(stderr, "Frame shift is %f secs.\n", frame_shift);

  TransitionModel trans_model;

  nnet2::AmNnet nnet;
  {
    bool binary;
    Input ki(nnet2_rxfilename, &binary);
    trans_model.Read(ki.Stream(), binary);
    nnet.Read(ki.Stream(), binary);
  }

  // This one is much slower than the others.
  fst::Fst<fst::StdArc>* decode_fst = ReadFstKaldi(fst_rxfilename);

  fst::SymbolTable* word_syms =
      fst::SymbolTable::ReadText(word_syms_rxfilename);
  fst::SymbolTable* phone_syms =
      fst::SymbolTable::ReadText(phone_syms_rxfilename);

  OnlineSilenceWeighting silence_weighting(
      trans_model, feature_info.silence_weighting_config);

  Hypothesizer hypothesizer(frame_shift, trans_model, word_boundary_info,
                            word_syms, phone_syms);

  kaldi::OnlineIvectorExtractorAdaptationState adaptation_state(
      feature_info.ivector_extractor_info);

  std::unique_ptr<Decoder> decoder(new Decoder(feature_info, trans_model,
                                               nnet2_decoding_config, nnet,
                                               decode_fst, adaptation_state));

  std::ostream& out_stream = std::cout;
  std::istream& in_stream = std::cin;

  RPCWriteReply(out_stream, STATUS_OK, "loaded");

  while (!in_stream.eof()) {
    string method;
    vector<string> args;
    vector<char> body;

    if (!RPCReadRequest(in_stream, &method, &args, &body)) {
      if (in_stream.eof()) {
        RPCWriteReply(out_stream, STATUS_BAD_REQUEST, "unexpected eof");
      } else {
        RPCWriteReply(out_stream, STATUS_BAD_REQUEST,
                      "malformed request '" + method + "'");
      }
      continue;
    }
    std::cerr << "method=" << method << std::endl;

    try {
      if (method == "stop") {
        RPCWriteReply(out_stream, STATUS_OK, "goodbye");
        return 0;

      } else if (method == "reset") {
        // Reset all decoding state.
        decoder.reset(new Decoder(feature_info, trans_model,
                                  nnet2_decoding_config, nnet, decode_fst,
                                  adaptation_state));
        RPCWriteReply(out_stream, STATUS_OK, "");

      } else if (method == "push-chunk") {
        // Add a chunk of audio to the decoding pipeline.
        int sample_count = body.size() / 2;

        Vector<BaseFloat> wave_part(sample_count);
        for (int i = 0; i < sample_count; i++) {
          int16_t sample = *reinterpret_cast<int16_t*>(&body[i * 2]);
          wave_part(i) = sample;
        }

        decoder->AddChunk(arate, wave_part);
        RPCWriteReply(out_stream, STATUS_OK, "");

      } else if (method == "get-partial") {
        // Dump the provisional (non-word-aligned) transcript for the current
        // lattice.

        kaldi::Lattice partial_lat = decoder->GetBestPath();
        Hypothesis partial = hypothesizer.GetPartial(partial_lat);
        string serialized = MarshalHypothesis(partial);

        RPCWriteReply(out_stream, STATUS_OK, serialized);

      } else if (method == "get-final") {
        // Dump the final, phone-aligned transcript for the current lattice.
        kaldi::Lattice final_lat = decoder->GetBestPath();
        Hypothesis final = hypothesizer.GetFull(final_lat);
        string serialized = MarshalHypothesis(final);

        RPCWriteReply(out_stream, STATUS_OK, serialized);

      } else {
        RPCWriteReply(out_stream, STATUS_BAD_REQUEST, "unknown method");
        continue;
      }

    } catch (const std::exception& e) {
      RPCWriteReply(out_stream, STATUS_INTERNAL_SERVER_ERROR, e.what());
      continue;
    }
  }

  return 0;
}
