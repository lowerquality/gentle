import csv
import io
import json

def to_ctm(tran):
	'''Return a CTM (http://www1.icsi.berkeley.edu/Speech/docs/sctk-1.2/infmts.htm#ctm_fmt_name_0)
	representation of the aligned transcript.

	For simplicity, the filename is always 'gentle' and the left (A)
	channel is always specified.
	'''
	buf = ''
	tokens = [tok for tok in tran['words'] if tok["case"] in ("success", "not-found-in-transcript")]
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

def to_json(tran, **kwargs):
	'''Return a JSON representation of the aligned transcript'''
	return json.dumps(tran, **kwargs)

def to_csv(tran):
	'''Return a CSV representation of the aligned transcript. Format:
	<word> <token> <start seconds> <end seconds>
	'''
	if not 'words' in tran:
		return ''
	buf = io.BytesIO()
	w = csv.writer(buf)
	for X in tran["words"]:
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
