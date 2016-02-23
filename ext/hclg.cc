#include "hclg.h"

#include "fst/script/compile.h"
#include "hmm/hmm-utils.h"

// Re-build the Kaldi decoding graph from its constituent parts.
// We do this so we can restrict the language model while doing
// forced alignment.
//
// More information on HCLG: http://kaldi.sourceforge.net/graph.html
const fst::VectorFst<fst::StdArc> BuildHCLG(
    const fst::VectorFst<fst::StdArc>& grammar_fst,
    const fst::VectorFst<fst::StdArc>& lang_disambig_fst,
    const kaldi::ContextDependency& ctx_dep,
    const kaldi::TransitionModel& trans_model,
    const std::vector<int32>& disambig_symbols) {
  int32 N = 3, P = 1;
  float transition_scale = 1.0;
  float self_loop_scale = 0.1;
  bool reverse = false;

  // Build LG FST
  if (lang_disambig_fst.Properties(fst::kOLabelSorted, true) == 0) {
    KALDI_WARN << "L_disambig.fst is not olabel sorted.";
  }
  fst::TableComposeOptions table_opts;
  fst::VectorFst<fst::StdArc> lg_fst;
  fst::TableCompose(lang_disambig_fst, grammar_fst, &lg_fst, table_opts);

  ArcSort(&lg_fst, fst::ILabelCompare<fst::StdArc>());
  int max_states = -1;
  bool debug_location = false;
  DeterminizeStarInLog(&lg_fst, fst::kDelta, &debug_location, max_states);

  MinimizeEncoded(&lg_fst, fst::kDelta);

  ArcSort(&lg_fst, fst::ILabelCompare<fst::StdArc>());

  fst::StdArc::Weight min, max;
  if (!IsStochasticFst(lg_fst, 0.01, &min, &max)) {
    std::cerr << "[info]: LG not stochastic." << std::endl;
  }

  // Build CLG FST
  std::vector<std::vector<int32>> ilabels;
  fst::VectorFst<fst::StdArc> clg_fst;
  std::vector<int32>& hack_disambig_nonconst =
      const_cast<std::vector<int32>&>(disambig_symbols);
  fst::ComposeContext(hack_disambig_nonconst, N, P, &lg_fst, &clg_fst,
                      &ilabels);

  ArcSort(&clg_fst, fst::ILabelCompare<fst::StdArc>());

  if (!IsStochasticFst(clg_fst, 0.01, &min, &max)) {
    std::cerr << "[info]: CLG not stochastic." << std::endl;
  }

  // Build HCLGa FST
  kaldi::HTransducerConfig hcfg;
  hcfg.transition_scale = transition_scale;
  if (reverse) {
    hcfg.reverse = true;
    hcfg.push_weights = true;
  }
  std::vector<int32> disambig_tid;
  fst::VectorFst<fst::StdArc>* ha_fst =
      GetHTransducer(ilabels, ctx_dep, trans_model, hcfg, &disambig_tid);

  fst::VectorFst<fst::StdArc> hclga_fst;
  fst::TableComposeOptions hclga_table_opts;
  TableCompose(*ha_fst, clg_fst, &hclga_fst, hclga_table_opts);

  ArcSort(&hclga_fst, fst::ILabelCompare<fst::StdArc>());
  DeterminizeStarInLog(&hclga_fst, fst::kDelta, &debug_location, max_states);

  RemoveSomeInputSymbols(disambig_tid, &hclga_fst);

  RemoveEpsLocal(&hclga_fst);

  MinimizeEncoded(&hclga_fst, fst::kDelta);

  if (!IsStochasticFst(hclga_fst, 0.01, &min, &max)) {
    std::cerr << "[info]: HCLGa is not stochastic." << std::endl;
  }

  // Build HCLG FST
  fst::VectorFst<fst::StdArc>& hclg_fst = hclga_fst;  // rewrites in place

  std::vector<int32> null_disambig_syms;
  AddSelfLoops(trans_model, null_disambig_syms, self_loop_scale, true,
               &hclg_fst);

  if (transition_scale == 1.0 && self_loop_scale == 1.0 &&
      !IsStochasticFst(hclg_fst, 0.01, &min, &max)) {
    std::cerr << "[info]: final HCLG is not stochastic." << std::endl;
  }

  return hclg_fst;
}
