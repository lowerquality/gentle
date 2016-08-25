import logging
from multiprocessing.pool import ThreadPool as Pool
import os
import wave

from gentle import standard_kaldi
from gentle import metasentence
from gentle import language_model
from gentle import diff_align

def prepare_multipass(alignment):
    to_realign = []
    last_aligned_word = None
    cur_unaligned_words = []

    for wd_idx,wd in enumerate(alignment):
        if wd['case'] == 'not-found-in-audio':
            cur_unaligned_words.append(wd)
        elif wd['case'] == 'success':
            if len(cur_unaligned_words) > 0:
                to_realign.append({
                    "start": last_aligned_word,
                    "end": wd,
                    "words": cur_unaligned_words})
                cur_unaligned_words = []

            last_aligned_word = wd

    if len(cur_unaligned_words) > 0:
        to_realign.append({
            "start": last_aligned_word,
            "end": None,
            "words": cur_unaligned_words})

    return to_realign
    
def realign(wavfile, alignment, ms, resources, nthreads=4, progress_cb=None):
    to_realign = prepare_multipass(alignment)
    realignments = []

    def realign(chunk):
        wav_obj = wave.open(wavfile, 'r')

        start_t = (chunk["start"] or {"end": 0})["end"]
        end_t = chunk["end"]
        if end_t is None:
            end_t = wav_obj.getnframes() / float(wav_obj.getframerate())
        else:
            end_t = end_t["start"]

        duration = end_t - start_t
        if duration < 0.01 or duration > 60:
            logging.debug("cannot realign %d words with duration %f" % (len(chunk['words']), duration))
            return

        # Create a language model
        offset_offset = chunk['words'][0]['startOffset']
        chunk_len = chunk['words'][-1]['endOffset'] - offset_offset
        chunk_transcript = ms.raw_sentence[offset_offset:offset_offset+chunk_len].encode("utf-8")
        chunk_ms = metasentence.MetaSentence(chunk_transcript, resources.vocab)
        chunk_ks = chunk_ms.get_kaldi_sequence()

        chunk_gen_hclg_filename = language_model.make_bigram_language_model(chunk_ks, resources.proto_langdir)
        k = standard_kaldi.Kaldi(
            resources.nnet_gpu_path,
            chunk_gen_hclg_filename,
            resources.proto_langdir)

        wav_obj = wave.open(wavfile, 'r')
        wav_obj.setpos(int(start_t * wav_obj.getframerate()))
        buf = wav_obj.readframes(int(duration * wav_obj.getframerate()))

        k.push_chunk(buf)
        ret = k.get_final()
        k.stop()

        word_alignment = diff_align.align(ret, chunk_ms)

        # Adjust startOffset, endOffset, and timing to match originals
        for wd in word_alignment:
            if wd.get("end"):
                # Apply timing offset
                wd['start'] += start_t
                wd['end'] += start_t

            if wd.get("endOffset"):
                wd['startOffset'] += offset_offset
                wd['endOffset'] += offset_offset

        # "chunk" should be replaced by "words"
        realignments.append({"chunk": chunk, "words": word_alignment})

        if progress_cb is not None:
            progress_cb({"percent": len(realignments) / float(len(to_realign))})

    pool = Pool(nthreads)
    pool.map(realign, to_realign)
    pool.close()

    # Sub in the replacements
    o_words = alignment
    for ret in realignments:
        st_idx = o_words.index(ret["chunk"]["words"][0])
        end_idx= o_words.index(ret["chunk"]["words"][-1])+1
        logging.debug('splice in: "%s' % (str(ret["words"])))
        logging.debug('splice out: "%s' % (str(o_words[st_idx:end_idx])))
        o_words = o_words[:st_idx] + ret["words"] + o_words[end_idx:]

    return o_words
