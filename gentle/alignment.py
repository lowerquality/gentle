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
	tokens = [token for token in alignment['tokens'] if 'time' in token]
	tokens = sorted(tokens, key=lambda token: token['time']['start'])
	for token in tokens:
		if 'source' in token:
			word = token['source']['text']
		else:
			word = token['alignedWord']
		word = word.upper()
		if word == '[OOV]':
			# TODO(maxhawkins): how are OOVs
			# usually represented by sctk?
			continue
		start = token['time']['start']
		duration = token['time']['duration']
		buf += 'gentle A %g %g %s\n' % (start, duration, word)
	return buf

def to_json(alignment, **kwargs):
	'''Return a JSON representation of the alignment'''
	return json.dumps(alignment, **kwargs)

def to_csv(alignment):
	'''Return a CSV representation of the alignment. Format:
	<word> <token> <start seconds> <duration seconds>
	'''
	if not 'tokens' in alignment:
		return ''
	buf = io.BytesIO()
	w = csv.writer(buf)
	for token in alignment["tokens"]:
		if token.get("case") not in ("success", "not-found-in-audio"):
			continue
		row = [
			token['source']['text'],
			token.get("alignedWord"),
			token['time']['start'],
			token['time']['duration'],
		]
		w.writerow(row)
	return buf.getvalue()
