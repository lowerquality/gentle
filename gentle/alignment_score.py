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

if __name__=='__main__':
	import argparse
	import json

	parser = argparse.ArgumentParser(
		description='Generate statistics about the quality of an alignment.')
	parser.add_argument('hypothesis', type=argparse.FileType('r'),
		help='generated transcript for testing')
	parser.add_argument('reference', type=argparse.FileType('r'),
		help='ground truth transcript to compare with')

	args = parser.parse_args()

	hypothesis = json.load(args.hypothesis)['words']
	reference = json.load(args.reference)['words']

	score = alignment_score(hypothesis, reference)
	for label, s in score.iteritems():
		print '%15s:  %.2f' % (label, s)
