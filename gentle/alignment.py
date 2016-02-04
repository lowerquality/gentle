import csv
import io
import json

def to_ctm(alignment):
	'''Return a CTM (http://www1.icsi.berkeley.edu/Speech/docs/sctk-1.2/infmts.htm#ctm_fmt_name_0)
	representation of the alignment.

	For simplicity, the filename is always 'gentle' and the left (A)
	channel is always specified.
	'''
	buf = ''
	tokens = [tok for tok in alignment['words'] if tok["case"] in ("success", "not-found-in-transcript")]
	tokens = sorted(tokens, key=lambda tok: tok['start'])
	for tok in tokens:
		if 'word' in tok:
			word = tok['word']
		else:
			word = tok['alignedWord']
		word = word.upper()
		if word == '[OOV]':
			# TODO(maxhawkins): how are OOVs
			# usually represented by sctk?
			continue
		start = tok['start']
		end = tok['end']
		duration = end - start
		buf += 'gentle A %g %g %s\n' % (start, duration, word)
	return buf

def to_json(alignment, **kwargs):
	'''Return a JSON representation of the alignment'''
	return json.dumps(alignment, **kwargs)

def to_csv(alignment):
	'''Return a CSV representation of the alignment. Format:
	<word> <token> <start seconds> <end seconds>
	'''
	if not 'words' in alignment:
		return ''
	buf = io.BytesIO()
	w = csv.writer(buf)
	for X in alignment["words"]:
		if X.get("case") not in ("success", "not-found-in-audio"):
			continue
		row = [
			X["word"],
			X.get("alignedWord"),
			X.get("start"),
			X.get("end")
		]
		w.writerow(row)
	return buf.getvalue()
