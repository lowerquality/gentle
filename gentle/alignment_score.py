import collections
import difflib

def alignment_score(hypothesis, reference):
	'''Generates a metric comparing the quality of a generated alignment
	to a reference alignment.

	The algorithm aligns the generated alignment to the reference alignment,
	ignoring tokens that don't contain a time. Then it runs the diff algorithm
	and returns the number of words correct, inserted, deleted, and substituted
	divided by the number of reference words.
	'''
	if len(reference) == 0:
		raise ValueError('missing reference text')

	def aligned_words(tran):
		for t in tran:
			if t['case'] == 'not-found-in-audio':
				continue
			yield t['alignedWord']
	ref_words = list(aligned_words(reference))
	hyp_words = list(aligned_words(hypothesis))

	# TODO(maxhawkins): refactor diff_align so we can use it here
	matcher = difflib.SequenceMatcher(a=ref_words, b=hyp_words)		
	counts = collections.defaultdict(float)
	for op, s1, e1, s2, e2 in matcher.get_opcodes():
		if op == 'delete':
			counts[op] += e1 - s1
		else:
			counts[op] += e2 - s2

	score =  {
		'inserted': counts['insert'],
		'correct': counts['equal'],
		'deleted': counts['delete'],
		'substituted': counts['replace'],
	}
	for k in score.keys():
		score[k] /= len(ref_words)
	score['error'] = score['inserted'] + score['deleted'] + score['substituted']

	return score

