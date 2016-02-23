#include "online2/online-nnet2-decoding.h"

const fst::VectorFst<fst::StdArc> BuildHCLG(
    const fst::VectorFst<fst::StdArc>& grammar_fst,
    const fst::VectorFst<fst::StdArc>& lang_disambig_fst,
    const kaldi::ContextDependency& ctx_dep,
    const kaldi::TransitionModel& trans_model,
    const std::vector<int32>& disambig_symbols);
