// online2 wav gmm latgen faster
#include "online2/online-feature-pipeline.h"
#include "online2/online-gmm-decoding.h"
#include "online2/onlinebin-util.h"
#include "online2/online-timing.h"
#include "online2/online-endpoint.h"
#include "fstext/fstext-lib.h"
#include "lat/lattice-functions.h"
#include "lat/word-align-lattice.h"

const int arate = 16000;

void ConfigFeatureInfo(kaldi::OnlineFeaturePipelineConfig config_)
{

  config_.feature_type = "mfcc";

  //mfcc config

  config_.mfcc_opts.frame_opts.samp_freq = arate;
  config_.mfcc_opts.use_energy = false;
  config_.mfcc_opts.num_ceps = 40;
  config_.mfcc_opts.mel_opts.num_bins = 40;
  config_.mfcc_opts.mel_opts.low_freq = 40;
  config_.mfcc_opts.mel_opts.high_freq = -200;
}

void ConfigDecoding(kaldi::OnlineGmmDecodingConfig &config)
{
  // Set Decoder Options
//   config.fmllr_lattice_beam = 3.0;
   config.acoustic_scale = 1.0; // changed from 0.1?
   config.faster_decoder_opts.lattice_beam = 6.0;
   config.faster_decoder_opts.beam = 13.0;
   config.faster_decoder_opts.max_active = 7000;
}

void ConfigEndpoint(kaldi::OnlineEndpointConfig &config)
{
    config.silence_phones = "1:2:3:4:5:6:7:8:9:10:11:12:13:14:15";
}

void usage()
{
  fprintf(stderr,"Usage: k3ss [options] <model_dir> <hclg_path> \n");
}
int main(int argc , char *argv[])
{
    setbuf(stdout,NULL);
    using namespace kaldi;
    using namespace fst;



  // config
    std::string model_dir = "exps/SpanishModel";
    std::string graph_dir = model_dir + "graph_pp";
    std::string fst_rxfilename = graph_dir + "/HCLG.fst";
    std::string word_syms_rxfilename = graph_dir + "words.txt";
    std::string phone_syms_rxfilename = graph_dir + "phones.txt";
    std::string word_boundary_filename = graph_dir + "phones/word_boundary.int";


     std::string model_rxfilename = model_dir + "/final.mdl";

     if(argc == 3) {
       model_dir = argv[1];
       graph_dir = model_dir + "/graph_pp";
       fst_rxfilename = argv[2];
     }
     else if(argc != 1) {
       usage();
       return EXIT_FAILURE;
     }


    // In module word-align-lattice.h
    WordBoundaryInfoNewOpts opts;
    WordBoundaryInfo word_boundary_info(opts, word_boundary_filename);

    OnlineFeaturePipelineCommandLineConfig feature_cmdline_config;
    OnlineFeaturePipelineConfig feature_info ;
    ConfigFeatureInfo(feature_info);
    OnlineGmmDecodingConfig sim_decoding_config;
    ConfigDecoding(sim_decoding_config);
    OnlineEndpointConfig endpoint_config;
    ConfigEndpoint(endpoint_config);

    BaseFloat frame_shift = feature_info.FrameShiftInSeconds();

    // Read Acoustic Model
    TransitionModel tmodel_;
    kaldi::AmDiagGmm model_;
    {
      bool binary;
      Input ki(model_rxfilename, &binary);
      tmodel_.Read(ki.Stream(), binary);
      model_.Read(ki.Stream(), binary);
    }

    //Reading decoding fst

    fst::Fst<fst::StdArc> *decode_fst = ReadFstKaldi(fst_rxfilename);

    fst::SymbolTable *word_syms =
      fst::SymbolTable::ReadText(word_syms_rxfilename);

    fst::SymbolTable* phone_syms =
      fst::SymbolTable::ReadText(phone_syms_rxfilename);


      OnlineFeaturePipelineConfig feature_config(feature_cmdline_config);
      OnlineFeaturePipeline pipeline_prototype(feature_config);
      OnlineGmmAdaptationState adaptation_state();
      OnlineFeaturePipeline feature_pipeline(feature_info);
  //    feature_pipeline.SetAdaptationState(adaptation_state);
  // No such function called SetAdaptation in online feature-pipeline.h
  // No silence weighting in this No ivectors

  SingleUtteranceGmmDecoder decoder(sim_decoding_config,
                                          model_,
                                        pipeline_prototype,
                                         *decode_fst, adaptation_state);

      char cmd[1024];

      while(true) {
        // Let the client decide what we should do...
        fgets(cmd, sizeof(cmd), stdin);

        if(strcmp(cmd,"stop\n") == 0) {
          break;
        }
        else if(strcmp(cmd,"reset\n") == 0) {
          feature_pipeline.~OnlineFeaturePipeline();
          new (&feature_pipeline) OnlineFeaturePipeline(feature_info);

          decoder.~SingleUtteranceGmmDecoder();
          new (&decoder) SingleUtteranceGmmDecoder(sim_decoding_config,
                                                     model_,
                                                     pipeline_prototype,
                                                     *decode_fst,
                                                     adaptation_state);
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

          for (int i = 0; i < chunk_len ; ++i) {
            (wave_part)(i) = static_cast<BaseFloat>(audio_chunk[i]);
          }

          decoder.FeaturePipeline().AcceptWaveform(arate, wave_part);

          std::vector<std::pair<int32, BaseFloat> > delta_weights;

          decoder.AdvanceDecoding();

          fprintf(stdout, "ok\n");
        }
        else if(strcmp(cmd, "get-final\n") == 0) {
          decoder.FeaturePipeline().InputFinished(); // XXX: this is new: what does it do?

          decoder.FinalizeDecoding();

           decoder.GetAdaptationState(&adaptation_state);

            bool end_of_utterance = true;
            decoder.EstimateFmllr(end_of_utterance);
            CompactLattice clat;
            bool rescore_if_needed = true;
            decoder.GetLattice(rescore_if_needed, end_of_utterance, &clat);

          // Compute prons alignment (see: kaldi/latbin/nbest-to-prons.cc)
          CompactLattice aligned_clat;

          std::vector<int32> words, times, lengths;
          std::vector<std::vector<int32> > prons;
          std::vector<std::vector<int32> > phone_lengths;

          WordAlignLattice(clat, tmodel_, word_boundary_info,
                           0, &aligned_clat);

          CompactLatticeToWordProns(tmodel_, aligned_clat, &words, &times,
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
