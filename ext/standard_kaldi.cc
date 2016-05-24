// Escape hatch from Kaldi.
//
// Use standard in/out trickery to get control flow into other languages.

// Based on online2-wav-nnet2-latgen-faster

#include <stdlib.h>

#include "online2/online-nnet2-decoding.h"
#include "online2/onlinebin-util.h"
#include "online2/online-timing.h"
#include "online2/online-endpoint.h"
#include "fst/script/compile.h"
#include "fstext/fstext-lib.h"
#include "lat/lattice-functions.h"
#include "lat/word-align-lattice.h"
#include "hmm/hmm-utils.h"
#include "thread/kaldi-thread.h"

#include "decoder.h"
#include "hclg.h"
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
  const string hclg_filename = argv[2];
  const string proto_lang_dir = argv[3];

  const string ctx_dep_filename = proto_lang_dir + "/modeldir/tree";
  const string disambig_phones_filename =
    proto_lang_dir + "/langdir/phones/disambig.int";
  const string lang_disambig_fst_filename =
      proto_lang_dir + "/langdir/L_disambig.fst";

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

  std::unique_ptr<fst::Fst<fst::StdArc>> hclg_fst;
  // Optionally load an existing decoding graph if it exists
  if (std::ifstream(hclg_filename.c_str())) {
    hclg_fst.reset(ReadFstKaldi(hclg_filename));
  }

  std::unique_ptr<const fst::SymbolTable> word_syms(
      fst::SymbolTable::ReadText(word_syms_rxfilename));
  std::unique_ptr<const fst::SymbolTable> phone_syms(
      fst::SymbolTable::ReadText(phone_syms_rxfilename));

  // Load BuildHCLG data
  std::unique_ptr<const VectorFst<StdArc>> lang_disambig_fst(
      ReadFstKaldi(lang_disambig_fst_filename));
  if (lang_disambig_fst->Properties(fst::kOLabelSorted, true) == 0) {
    KALDI_WARN << "L_disambig.fst is not olabel sorted.";
  }
  std::vector<int32> disambig_symbols;
  ReadIntegerVectorSimple(disambig_phones_filename, &disambig_symbols);
  if (disambig_symbols.empty()) {
    KALDI_WARN << "Disambiguation symbols list is empty; this likely "
               << "indicates an error in data preparation.";
  }
  ContextDependency ctx_dep;
  ReadKaldiObject(ctx_dep_filename, &ctx_dep);

  OnlineSilenceWeighting silence_weighting(
      trans_model, feature_info.silence_weighting_config);

  Hypothesizer hypothesizer(frame_shift, trans_model, word_boundary_info,
                            word_syms.get(), phone_syms.get());

  kaldi::OnlineIvectorExtractorAdaptationState adaptation_state(
      feature_info.ivector_extractor_info);

  std::unique_ptr<Decoder> current_decoder;

  auto get_decoder = [&]() -> Decoder* {
    Decoder *decoder = current_decoder.get();
    if (decoder != nullptr) {
      return decoder;
    }
    if (hclg_fst.get() == nullptr) {
      throw "no model loaded";
    }
    current_decoder.reset(new Decoder(feature_info, trans_model,
                                      nnet2_decoding_config, nnet,
                                      hclg_fst.get(), adaptation_state));
    return current_decoder.get();
  };

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

    try {
      if (method == "stop") {
        RPCWriteReply(out_stream, STATUS_OK, "goodbye");
        return 0;

      } else if (method == "reset") {
        // Reset all decoding state.
        current_decoder.reset(nullptr);
        RPCWriteReply(out_stream, STATUS_OK, "");

      } else if (method == "make-model") {
        // Make a new model using the grammar provided in body.
        // It will be used the next time the decoder is reset.
        fst::SymbolTableTextOptions opts;

        std::stringstream body_stream(string(body.begin(), body.end()));

        fst::FstCompiler<fst::StdArc> fstcompiler(
            body_stream, "", word_syms.get(), word_syms.get(), nullptr, false,
            false, false, false, false);
        VectorFst<StdArc> grammar_fst = fstcompiler.Fst();

        hclg_fst.reset(new VectorFst<StdArc>(
            BuildHCLG(grammar_fst, *lang_disambig_fst, ctx_dep, trans_model,
                      disambig_symbols)));

        RPCWriteReply(out_stream, STATUS_OK, "");

      } else if (method == "push-chunk") {
        // Add a chunk of audio to the decoding pipeline.
        int sample_count = body.size() / 2;

        Vector<BaseFloat> wave_part(sample_count);
        for (int i = 0; i < sample_count; i++) {
          int16_t sample = *reinterpret_cast<int16_t*>(&body[i * 2]);
          wave_part(i) = sample;
        }

        auto decoder = get_decoder();
        decoder->AddChunk(arate, wave_part);
        RPCWriteReply(out_stream, STATUS_OK, "");

      } else if (method == "get-partial") {
        // Dump the provisional (non-word-aligned) transcript for the current
        // lattice.

        auto decoder = get_decoder();
        kaldi::Lattice partial_lat = decoder->GetBestPath();
        Hypothesis partial = hypothesizer.GetPartial(partial_lat);
        string serialized = MarshalHypothesis(partial);

        RPCWriteReply(out_stream, STATUS_OK, serialized);

      } else if (method == "get-final") {
        // Dump the final, phone-aligned transcript for the current lattice.
        auto decoder = get_decoder();
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
