import csv
import io
import json

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
