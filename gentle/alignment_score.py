import collections
import difflib

from diff_align import word_diff

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

	counts = collections.defaultdict(float)
	for op, _, _ in word_diff(ref_words, hyp_words):
		counts[op] += 1

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

