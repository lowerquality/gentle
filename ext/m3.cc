#include "fstext/context-fst.h"
#include "fstext/fstext-utils.h"
#include "fstext/kaldi-fst-io.h"
#include "fstext/table-matcher.h"
#include "hmm/hmm-utils.h"
#include "hmm/transition-model.h"
#include "tree/context-dep.h"
#include "lat/lattice-functions-transition-model.h"
#include "util/common-utils.h"
#include <fst/script/arcsort.h>
#include <fst/script/compile.h>

int main(int argc, char *argv[]) {
	using namespace kaldi;
	using namespace fst;
	using fst::script::ArcSort;
	try {
		const char *usage = "Usage: ./mkgraph [options] <proto-dir> <grammar-fst> <out-fst>\n";

		ParseOptions po(usage);
		po.Read(argc, argv);
		if (po.NumArgs() != 3) {
			po.PrintUsage();
			return 1;
		}

		int32 N = 3, P = 1;
		float transition_scale = 1.0;
		float self_loop_scale = 0.1;

		std::string proto_dir = po.GetArg(1),
					grammar_fst_filename = po.GetArg(2),
					out_filename = po.GetArg(3);

		std::string lang_fst_filename = proto_dir + "/langdir/L.fst",
			lang_disambig_fst_filename = proto_dir + "/langdir/L_disambig.fst",
			disambig_phones_filename = proto_dir + "/langdir/phones/disambig.int",
			model_filename = proto_dir + "/tdnn_7b_chain_online/final.mdl",
			tree_filename = proto_dir + "/tdnn_7b_chain_online/tree",
			words_filename = proto_dir + "/tdnn_7b_chain_online/graph_pp/words.txt";

		if (!std::ifstream(lang_fst_filename.c_str())) {
			std::cerr << "expected " << lang_fst_filename << " to exist" << std::endl;
			return 1;
		}
		if (!std::ifstream(lang_disambig_fst_filename.c_str())) {
			std::cerr << "expected " << lang_disambig_fst_filename << " to exist" << std::endl;
			return 1;
		}
		if (!std::ifstream(grammar_fst_filename.c_str())) {
			std::cerr << "expected " << grammar_fst_filename << " to exist" << std::endl;
			return 1;
		}
		if (!std::ifstream(disambig_phones_filename.c_str())) {
			std::cerr << "expected " << disambig_phones_filename << " to exist" << std::endl;
			return 1;
		}
		if (!std::ifstream(model_filename.c_str())) {
			std::cerr << "expected " << model_filename << " to exist" << std::endl;
			return 1;
		}
		if (!std::ifstream(tree_filename.c_str())) {
			std::cerr << "expected " << tree_filename << " to exist" << std::endl;
			return 1;
		}

		// fstcompile
		const SymbolTable *ssyms = 0;
		fst::SymbolTableTextOptions opts;
		const SymbolTable *isyms = SymbolTable::ReadText(words_filename, opts);
		if (!isyms) { return 1; }
		const SymbolTable *osyms = SymbolTable::ReadText(words_filename, opts);
		if (!osyms) { return 1; }
		std::ifstream grammar_fst_file(grammar_fst_filename.c_str());
		FstCompiler<StdArc> fstcompiler(grammar_fst_file, "", isyms,
			osyms, ssyms,
			false, false,
			false, false,
			false);
		VectorFst<StdArc> grammar_fst = fstcompiler.Fst();

		// fsttablecompose
		VectorFst<StdArc> *lang_disambig_fst = ReadFstKaldi(lang_disambig_fst_filename);
		if (lang_disambig_fst->Properties(fst::kOLabelSorted, true) == 0) {
			KALDI_WARN << "L_disambig.fst is not olabel sorted.";
		}
		TableComposeOptions table_opts;
		VectorFst<StdArc> lg_fst;
		TableCompose(*lang_disambig_fst, grammar_fst, &lg_fst, table_opts);
		delete lang_disambig_fst;

		// fstdeterminizestar --use-log
		ArcSort(&lg_fst, ILabelCompare<StdArc>());
		int max_states = -1;
		bool debug_location = false;
		DeterminizeStarInLog(&lg_fst, kDelta, &debug_location, max_states);

		// fstminimizeencoded
		MinimizeEncoded(&lg_fst, kDelta);

		// fstarcsort --sort_type=ilabel
		ArcSort(&lg_fst, ILabelCompare<StdArc>());

		// fstisstochastic
		StdArc::Weight min, max;
		if (!IsStochasticFst(lg_fst, 0.01, &min, &max)) {
			std::cerr << "[info]: LG not stochastic." << std::endl;
		}

		// fstcomposecontext
		std::vector<int32> disambig_symbols;
		ReadIntegerVectorSimple(disambig_phones_filename, &disambig_symbols);
		if (disambig_symbols.empty()) {
			KALDI_WARN << "Disambiguation symbols list is empty; this likely "
				<< "indicates an error in data preparation.";
		}
		std::vector<std::vector<int32> > ilabels;
		VectorFst<StdArc> clg_fst;
		ComposeContext(disambig_symbols, N, P, &lg_fst, &clg_fst, &ilabels);

		// fstarcsort --sort_type=ilabel
		ArcSort(&clg_fst, ILabelCompare<StdArc>());

		// fstisstochastic
		if (!IsStochasticFst(clg_fst, 0.01, &min, &max)) {
			std::cerr << "[info]: CLG not stochastic." << std::endl;
		}

		// make-h-transducer
		HTransducerConfig hcfg;
		hcfg.transition_scale = transition_scale;
		ContextDependency ctx_dep;
		ReadKaldiObject(tree_filename, &ctx_dep);
		TransitionModel trans_model;
		ReadKaldiObject(model_filename, &trans_model);
		std::vector<int32> disambig_tid;
		fst::VectorFst<fst::StdArc> *ha_fst = GetHTransducer(
			ilabels,
			ctx_dep,
			trans_model,
			hcfg,
			&disambig_tid);

		// fsttablecompose
		VectorFst<StdArc> hclga_fst;
		TableComposeOptions hclga_table_opts;
		TableCompose(*ha_fst, clg_fst, &hclga_fst, hclga_table_opts);

		// fstdeterminizestar --use-log=true
		ArcSort(&hclga_fst, ILabelCompare<StdArc>());
		DeterminizeStarInLog(&hclga_fst, kDelta, &debug_location, max_states);

		// fstrmsymbols
		RemoveSomeInputSymbols(disambig_tid, &hclga_fst);

		// fstrmepslocal
		RemoveEpsLocal(&hclga_fst);

		// fstminimizeencoded
		MinimizeEncoded(&hclga_fst, kDelta);

		// fstisstochastic
		if (!IsStochasticFst(hclga_fst, 0.01, &min, &max)) {
			std::cerr << "[info]: HCLGa is not stochastic." << std::endl;
		}

		VectorFst<StdArc> hclg_fst = hclga_fst;

		// add-self-loops
		std::vector<int32> null_disambig_syms;
		AddSelfLoops(trans_model,
	                 null_disambig_syms,
	                 self_loop_scale,
	                 true,
			 true,
	                 &hclg_fst);

	    // fstisstochastic
		if (transition_scale == 1.0 &&
			self_loop_scale == 1.0 &&
			!IsStochasticFst(hclg_fst, 0.01, &min, &max)) {
			std::cerr << "[info]: final HCLG is not stochastic." << std::endl;
		}

	    if (!hclg_fst.Write(out_filename)) {
			KALDI_ERR << "error writing FST to " << out_filename;
	    }
	} catch(const std::exception &e) {
		std::cerr << e.what();
		return -1;
	}
}
