// refactor of online2-wav-nnet3-latgen-faster.cc

#include "online2/online-nnet3-decoding.h"
#include "online2/online-nnet2-feature-pipeline.h"
#include "online2/onlinebin-util.h"
#include "online2/online-timing.h"
#include "online2/online-endpoint.h"
#include "fstext/fstext-lib.h"
#include "lat/lattice-functions.h"
#include "lat/lattice-functions-transition-model.h"
#include "lat/word-align-lattice.h"
#include "nnet3/decodable-simple-looped.h"

#ifdef HAVE_CUDA
#include "cudamatrix/cu-device.h"
#endif

const int arate = 8000;

void ConfigFeatureInfo(kaldi::OnlineNnet2FeaturePipelineInfo& info,
                       std::string ivector_model_dir) {
    // Configure inline to avoid absolute paths in ".conf" files

    info.feature_type = "mfcc";
    info.use_ivectors = true;

    // ivector_extractor.conf
    ReadKaldiObject(ivector_model_dir + "/final.mat",
                    &info.ivector_extractor_info.lda_mat);
    ReadKaldiObject(ivector_model_dir + "/global_cmvn.stats",
                    &info.ivector_extractor_info.global_cmvn_stats);
    ReadKaldiObject(ivector_model_dir + "/final.dubm",
                    &info.ivector_extractor_info.diag_ubm);
    ReadKaldiObject(ivector_model_dir + "/final.ie",
                    &info.ivector_extractor_info.extractor);

    info.ivector_extractor_info.num_gselect = 5;
    info.ivector_extractor_info.min_post = 0.025;
    info.ivector_extractor_info.posterior_scale = 0.1;
    info.ivector_extractor_info.max_remembered_frames = 1000;
    info.ivector_extractor_info.max_count = 100; // changed from 0.0 (?)

    // XXX: Where do these come from?
    info.ivector_extractor_info.greedy_ivector_extractor = true;
    info.ivector_extractor_info.ivector_period = 10;
    info.ivector_extractor_info.num_cg_iters = 15;
    info.ivector_extractor_info.use_most_recent_ivector = true;

    // splice.conf
    info.ivector_extractor_info.splice_opts.left_context = 3;
    info.ivector_extractor_info.splice_opts.right_context = 3;

    // mfcc.conf
    info.mfcc_opts.frame_opts.samp_freq = arate;
    info.mfcc_opts.use_energy = false;
    info.mfcc_opts.num_ceps = 40;
    info.mfcc_opts.mel_opts.num_bins = 40;
    info.mfcc_opts.mel_opts.low_freq = 40;
    info.mfcc_opts.mel_opts.high_freq = -200;

    info.ivector_extractor_info.Check();
}

void ConfigDecoding(kaldi::LatticeFasterDecoderConfig& config) {
  config.lattice_beam = 6.0;
  config.beam = 15.0;
  config.max_active = 7000;
}

void ConfigEndpoint(kaldi::OnlineEndpointConfig& config) {
  config.silence_phones = "1:2:3:4:5:6:7:8:9:10:11:12:13:14:15:16:17:18:19:20";
}
void usage() {
  fprintf(stderr, "usage: k3 [nnet_dir hclg_path]\n");
}

int main(int argc, char *argv[]) {
    using namespace kaldi;
    using namespace fst;

    setbuf(stdout, NULL);

    std::string nnet_dir = "exp/tdnn_7b_chain_online";
    std::string graph_dir = nnet_dir + "/graph_pp";
    std::string fst_rxfilename = graph_dir + "/HCLG.fst";

    if(argc == 3) {
      nnet_dir = argv[1];
      graph_dir = nnet_dir + "/graph_pp";
      fst_rxfilename = argv[2];
    }
    else if(argc != 1) {
      usage();
      return EXIT_FAILURE;
    }

#ifdef HAVE_CUDA
    fprintf(stdout, "Cuda enabled\n");
    CuDevice &cu_device = CuDevice::Instantiate();
    cu_device.SetVerbose(true);
    cu_device.SelectGpuId("yes");
    fprintf(stdout, "active gpu: %d\n", cu_device.ActiveGpuId());
#endif
    const std::string ivector_model_dir = nnet_dir + "/ivector_extractor";
    const std::string nnet3_rxfilename = nnet_dir + "/final.mdl";

    const std::string word_syms_rxfilename = graph_dir + "/words.txt";
    const string word_boundary_filename = graph_dir + "/phones/word_boundary.int";
    const string phone_syms_rxfilename = graph_dir + "/phones.txt";

    WordBoundaryInfoNewOpts opts; // use default opts
    WordBoundaryInfo word_boundary_info(opts, word_boundary_filename);

    OnlineNnet2FeaturePipelineInfo feature_info;
    ConfigFeatureInfo(feature_info, ivector_model_dir);
    LatticeFasterDecoderConfig nnet3_decoding_config;
    ConfigDecoding(nnet3_decoding_config);
    OnlineEndpointConfig endpoint_config;
    ConfigEndpoint(endpoint_config);


    BaseFloat frame_shift = feature_info.FrameShiftInSeconds();

    TransitionModel trans_model;
    nnet3::AmNnetSimple am_nnet;
    {
      bool binary;
      Input ki(nnet3_rxfilename, &binary);
      trans_model.Read(ki.Stream(), binary);
      am_nnet.Read(ki.Stream(), binary);
    }

    nnet3::NnetSimpleLoopedComputationOptions nnet_simple_looped_opts;
    nnet_simple_looped_opts.acoustic_scale = 1.0; // changed from 0.1?

    nnet3::DecodableNnetSimpleLoopedInfo de_nnet_simple_looped_info(nnet_simple_looped_opts, &am_nnet);

    fst::Fst<fst::StdArc> *decode_fst = ReadFstKaldi(fst_rxfilename);

    fst::SymbolTable *word_syms =
      fst::SymbolTable::ReadText(word_syms_rxfilename);

    fst::SymbolTable* phone_syms =
      fst::SymbolTable::ReadText(phone_syms_rxfilename);


    OnlineIvectorExtractorAdaptationState adaptation_state(feature_info.ivector_extractor_info);

    OnlineNnet2FeaturePipeline feature_pipeline(feature_info);
    feature_pipeline.SetAdaptationState(adaptation_state);

    OnlineSilenceWeighting silence_weighting(
                                             trans_model,
                                             feature_info.silence_weighting_config);

    SingleUtteranceNnet3Decoder decoder(nnet3_decoding_config,
                                        trans_model,
					de_nnet_simple_looped_info,
                                        //am_nnet, // kaldi::nnet3::DecodableNnetSimpleLoopedInfo
                                        *decode_fst,
                                        &feature_pipeline);


  char cmd[1024];

  while(true) {
    // Let the client decide what we should do...
    fgets(cmd, sizeof(cmd), stdin);

    if(strcmp(cmd,"stop\n") == 0) {
      break;
    }
    else if(strcmp(cmd,"reset\n") == 0) {
      feature_pipeline.~OnlineNnet2FeaturePipeline();
      new (&feature_pipeline) OnlineNnet2FeaturePipeline(feature_info);

      decoder.~SingleUtteranceNnet3Decoder();
      new (&decoder) SingleUtteranceNnet3Decoder(nnet3_decoding_config,
                                                 trans_model,
						 de_nnet_simple_looped_info,
                                                 //am_nnet,
                                                 *decode_fst,
                                                 &feature_pipeline);
    }
    else if(strcmp(cmd,"push-chunk\n") == 0) {

      // Get chunk length from python
      int chunk_len;
      fgets(cmd, sizeof(cmd), stdin);
      sscanf(cmd, "%d\n", &chunk_len);

      int16_t audio_chunk[chunk_len];
      Vector<BaseFloat> wave_part = Vector<BaseFloat>(chunk_len);

      fread(&audio_chunk, 2, chunk_len, stdin);

      // We need to copy this into the `wave_part' Vector<BaseFloat> thing.
      // From `gst-audio-source.cc' in gst-kaldi-nnet2
      for (int i = 0; i < chunk_len ; ++i) {
        (wave_part)(i) = static_cast<BaseFloat>(audio_chunk[i]);
      }

      feature_pipeline.AcceptWaveform(arate, wave_part);

      std::vector<std::pair<int32, BaseFloat> > delta_weights;
      if (silence_weighting.Active()) {
        silence_weighting.ComputeCurrentTraceback(decoder.Decoder());
        silence_weighting.GetDeltaWeights(feature_pipeline.NumFramesReady(),
                                          &delta_weights);
        feature_pipeline.IvectorFeature()->UpdateFrameWeights(delta_weights);
      }

      decoder.AdvanceDecoding();

      fprintf(stdout, "ok\n");
    }
    else if(strcmp(cmd, "get-final\n") == 0) {
      feature_pipeline.InputFinished(); // Computes last few frames of input
      decoder.AdvanceDecoding();        // Decodes remaining frames
      decoder.FinalizeDecoding();

      Lattice final_lat;
      decoder.GetBestPath(true, &final_lat);
      CompactLattice clat;
      ConvertLattice(final_lat, &clat);

      // Compute prons alignment (see: kaldi/latbin/nbest-to-prons.cc)
      CompactLattice aligned_clat;

      std::vector<int32> words, times, lengths;
      std::vector<std::vector<int32> > prons;
      std::vector<std::vector<int32> > phone_lengths;

      WordAlignLattice(clat, trans_model, word_boundary_info,
                       0, &aligned_clat);

      CompactLatticeToWordProns(trans_model, aligned_clat, &words, &times,
                                &lengths, &prons, &phone_lengths);

      for (int i = 0; i < words.size(); i++) {
        if(words[i] == 0) {
          // <eps> links - silence
          continue;
        }
        fprintf(stdout, "word: %s / start: %f / duration: %f\n",
                word_syms->Find(words[i]).c_str(),
                times[i] * frame_shift,
                lengths[i] * frame_shift);
        // Print out the phonemes for this word
        for(size_t j=0; j<phone_lengths[i].size(); j++) {
          fprintf(stdout, "phone: %s / duration: %f\n",
                  phone_syms->Find(prons[i][j]).c_str(),
                  phone_lengths[i][j] * frame_shift);
        }
      }

      fprintf(stdout, "done with words\n");

    }
    else {

      fprintf(stderr, "unknown command %s\n", cmd);

    }
  }
}
