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

void usage() {
  fprintf(stderr, "usage: standard_kaldi model_filename\n");
}

int main(int argc, char *argv[]) {
  using namespace kaldi;
  using namespace fst;

  if (argc != 2) {
    usage();
    return EXIT_FAILURE;
  }

  setbuf(stdout, NULL);

  const string nnet2_rxfilename = "PROTO_LANGDIR/modeldir/final.mdl";
  const string fst_rxfilename = argv[1];
  const string word_syms_rxfilename = "PROTO_LANGDIR/langdir/words.txt";
  const string phone_syms_rxfilename = "PROTO_LANGDIR/langdir/phones.txt";  
  const string word_boundary_filename = "PROTO_LANGDIR/langdir/phones/word_boundary.int";

  const int arate = 8000;
  const int chunk_len = 16000;    // 2sec

  OnlineNnet2FeaturePipelineConfig feature_config;  
  OnlineNnet2DecodingConfig nnet2_decoding_config;
  OnlineEndpointConfig endpoint_config;

  std::cerr << "Loading...\n";
  
  kaldi::ParseOptions po("");
  
  feature_config.Register(&po);
  nnet2_decoding_config.Register(&po);
  endpoint_config.Register(&po);

  // HACK(maxhawkins): omg
  const char* args[] = {
    "",
    "--max-active=7000",
    "--beam=15.0",
    "--lattice-beam=6.0",
    "--acoustic-scale=0.1",
    "--config=data/nnet_a_gpu_online/conf/online_nnet2_decoding.conf",
  };
  po.Read(6, args);

  WordBoundaryInfoNewOpts opts; // use default opts
  WordBoundaryInfo* word_boundary_info = new WordBoundaryInfo(opts, word_boundary_filename);
  
  OnlineNnet2FeaturePipelineInfo feature_info(feature_config);

  // !online (what does that mean?)
  feature_info.ivector_extractor_info.use_most_recent_ivector = true;
  feature_info.ivector_extractor_info.greedy_ivector_extractor = true;

  // Hardcode MFCC sample rate (?!)
  // HACKKK!K!
  feature_info.mfcc_opts.frame_opts.samp_freq = arate;

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
  fst::Fst<fst::StdArc> *decode_fst = ReadFstKaldi(fst_rxfilename);

    
  fst::SymbolTable *word_syms = fst::SymbolTable::ReadText(word_syms_rxfilename);
  fst::SymbolTable *phone_syms = fst::SymbolTable::ReadText(phone_syms_rxfilename);  

  std::cerr << "Loaded!\n";

  //const int chunk_len = 16;

  // XXX: should be int16?
  //static uint8_t *audio_chunk; //[chunk_len*sizeof(uint8_t)];
  //uint8_t audio_chunk[chunk_len*2];
  int16_t audio_chunk[chunk_len];  

  Vector<BaseFloat> wave_part = Vector<BaseFloat>(chunk_len);
  
  //audio_chunk = (uint8_t *)malloc(chunk_len*2);

  OnlineIvectorExtractorAdaptationState adaptation_state(feature_info.ivector_extractor_info);

  OnlineNnet2FeaturePipeline feature_pipeline(feature_info);
  feature_pipeline.SetAdaptationState(adaptation_state);

  OnlineSilenceWeighting silence_weighting(
                                           trans_model,
                                           feature_info.silence_weighting_config);
  
  SingleUtteranceNnet2Decoder decoder(nnet2_decoding_config,
                                      trans_model,
                                      nnet,
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
      // Reset all decoding state.
      
      // TODO(rmo): maxhawkins' `reset' semantics seems like a c++11 thing.
      // XXX: This seems inelegant. Maybe we should encapsulate as in gstreamer?
      feature_pipeline.~OnlineNnet2FeaturePipeline();
      new (&feature_pipeline) OnlineNnet2FeaturePipeline(feature_info);
      decoder.~SingleUtteranceNnet2Decoder();
      new (&decoder) SingleUtteranceNnet2Decoder(nnet2_decoding_config,
                                                trans_model,
                                                nnet,
                                                *decode_fst,
                                                // TODO(maxahawkins): does this take ownership?
                                                // TODO(rmo): what does `ownership' mean? (and `get' is c++11?)
                                            &feature_pipeline);

      adaptation_state.~OnlineIvectorExtractorAdaptationState();
      new (&adaptation_state) OnlineIvectorExtractorAdaptationState(feature_info.ivector_extractor_info);
      feature_pipeline.SetAdaptationState(adaptation_state);
    }
    else if(strcmp(cmd,"continue\n") == 0) {
      // Update iVectors and continue with current speaker
      feature_pipeline.GetAdaptationState(&adaptation_state);

      decoder.~SingleUtteranceNnet2Decoder();
      new (&decoder) SingleUtteranceNnet2Decoder(nnet2_decoding_config,
                                                trans_model,
                                                nnet,
                                                *decode_fst,
                                                // TODO(maxahawkins): does this take ownership?
                                                // TODO(rmo): what does `ownership' mean? (and `get' is c++11?)
                                            &feature_pipeline);

    }
    else if(strcmp(cmd,"push-chunk\n") == 0) {
      fread(&audio_chunk, 2, chunk_len, stdin);
      
      // Yikes! We need to copy this into the `wave_part' Vector<BaseFloat> thing.
      // This should not need to exist.
      // From `gst-audio-source.cc' in gst-kaldi-nnet2
      for (int i = 0; i < chunk_len ; ++i) {
        (wave_part)(i) = static_cast<BaseFloat>(audio_chunk[i]);
      }

      feature_pipeline.AcceptWaveform(arate, wave_part);

      // What does this do?
      std::vector<std::pair<int32, BaseFloat> > delta_weights;
      if (silence_weighting.Active()) {
        silence_weighting.ComputeCurrentTraceback(decoder.Decoder());
        silence_weighting.GetDeltaWeights(feature_pipeline.NumFramesReady(),
                                          &delta_weights);
        feature_pipeline.UpdateFrameWeights(delta_weights);
      }

      
      decoder.AdvanceDecoding();

      // TODO: make sure we've pushed at least one chunk...
      // if(decoder.EndpointDetected(endpoint_config)) {
      //   fprintf(stdout, "end\n");
      // }
      // else {
        fprintf(stdout, "ok\n");
      // }
    }
    else if(strcmp(cmd, "get-transitions\n") == 0) {
      // Dump transition information (for phoneme introspection)
      std::vector<std::string> names(phone_syms->NumSymbols());
      for (size_t i = 0; i < phone_syms->NumSymbols(); i++) {
        names[i] = phone_syms->Find(i);
      }

      trans_model.Print(std::cout,
                        names,
                        NULL);

      fprintf(stdout, "done with transitions\n");
    }
    else if(strcmp(cmd, "get-lattice\n") == 0) {
      // Dump lattice
      CompactLattice clat;
      decoder.GetLattice(false, &clat);

      WriteCompactLattice(std::cout,
                          false,
                          clat);
      fprintf(stdout, "done with lattice\n");
    }
    else if(strcmp(cmd, "get-final-lattice\n") == 0) {
      // Dump "final" lattice
      decoder.FinalizeDecoding();

      CompactLattice clat;
      decoder.GetLattice(true, &clat);

      // aligning the lattice makes it huge & unwieldy.
      CompactLattice aligned_clat;      
      WordAlignLattice(clat, trans_model, *word_boundary_info, 0, &aligned_clat);      

      WriteCompactLattice(std::cout,
                          false,
                          aligned_clat);

      fprintf(stdout, "done with lattice\n");
    }
    else if(strcmp(cmd,"get-partial\n") == 0) {
      Lattice lat;
      decoder.GetBestPath(false, &lat);

      // Let's see what words are in here..

      std::vector<int32> words;
      std::vector<int32> alignment;
      LatticeWeight weight;
      GetLinearSymbolSequence(lat, &alignment, &words, &weight);

      std::stringstream sentence;
      for (size_t i = 0; i < words.size(); i++) {
        std::string s = word_syms->Find(words[i]);
        if (i > 0) {
          sentence << " ";
        }
        sentence << s;
      }
      fprintf(stdout, "%s\n", sentence.str().c_str());
    }
    else if(strcmp(cmd,"get-final\n") == 0) {
      decoder.FinalizeDecoding();

      Lattice lat;
      decoder.GetBestPath(true, &lat);
      CompactLattice clat;
      ConvertLattice(lat, &clat);

      // Compute word alignment
      CompactLattice aligned_clat;
      std::vector<int32> words, times, lengths;
      WordAlignLattice(clat, trans_model, *word_boundary_info, 0, &aligned_clat);
      CompactLatticeToWordAlignment(aligned_clat, &words, &times, &lengths);

      for (size_t i = 0; i < words.size(); i++) {
        if (words[i] == 0)  {
          // Don't output anything for <eps> links, which correspond to silence....
          continue;
        }
        fprintf(stdout, "word: %s / start: %f / duration: %f\n",
                word_syms->Find(words[i]).c_str(),
                times[i] * frame_shift,
                lengths[i] * frame_shift);
      }

      fprintf(stdout, "done with words\n");
    }
  else if(strcmp(cmd,"peek-final\n") == 0) {
    // Same as `get-final,', but does not finalize decoding

    Lattice lat;
    decoder.GetBestPath(false, &lat);
    CompactLattice clat;
    ConvertLattice(lat, &clat);

    // Compute word alignment
    CompactLattice aligned_clat;
    std::vector<int32> words, times, lengths;
    WordAlignLattice(clat, trans_model, *word_boundary_info, 0, &aligned_clat);
    CompactLatticeToWordAlignment(aligned_clat, &words, &times, &lengths);

    for (size_t i = 0; i < words.size(); i++) {
      if (words[i] == 0)  {
        // Don't output anything for <eps> links, which correspond to silence....
        continue;
      }
      fprintf(stdout, "word: %s / start: %f / duration: %f\n",
              word_syms->Find(words[i]).c_str(),
              times[i] * frame_shift,
              lengths[i] * frame_shift);
    }

    fprintf(stdout, "done with words\n");
  }
  }


  std::cerr << "Goodbye.\n";  
  return 0;
}
