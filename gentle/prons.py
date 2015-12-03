import logging

def tweak(words, max_offset=0.2):
    # Strip silence from ends of words
    for wd in words:
        if len(wd['phones']) > 0 and wd['phones'][0]['phone'] == 'sil':
            p = wd['phones'].pop(0)
            wd['start'] += p['duration']
            wd['duration'] -= p['duration']

        if len(wd['phones']) > 0 and wd['phones'][-1]['phone'] == 'sil':
            p = wd['phones'].pop()
            wd['duration'] -= p['duration']
    
    # Move mis-aligned phonemes
    last_wd = None
    next_phonemes = []
    for wd in words:
        if len(next_phonemes) > 0:
            # Add the previous phonemes
            duration = sum([X['duration'] for X in next_phonemes])

            # Merge if the edge is identical
            if len(wd['phones']) > 0 and next_phonemes[-1]['phone'] == wd['phones'][0]['phone']:
                wd['phones'][0]['duration'] += next_phonemes[-1]['duration']
                next_phonemes = next_phonemes[:-1]

            wd['phones'] = next_phonemes + wd['phones']
            wd['start'] -= duration
            wd['duration'] += duration

            next_phonemes = []

        # Did we get the end of the last word
        elif len(wd['phones']) >= 1 \
             and last_wd is not None \
             and wd['phones'][0]['phone'][-1] in 'ES' \
             and (len(last_wd['phones']) == 0 or \
                  (not last_wd['phones'][-1]['phone'].endswith('_E')) \
                   or last_wd['phones'][-1]['phone'] == wd['phones'][0]['phone']):
             
            logging.info('moving the end back')
            logging.info('last_wd: %s', str(last_wd))
            logging.info('wd: %s', str(wd))
            
            first_phone = wd['phones'][0]
            wd['phones'] = wd['phones'][1:]
            wd['duration'] -= first_phone['duration']
            wd['start'] += first_phone['duration']

            if len(last_wd['phones']) > 0 and last_wd['phones'][-1]['phone'] == first_phone['phone']:
                last_wd['phones'][-1]['duration'] += first_phone['duration']
            else:
                last_wd['phones'].append(first_phone)
            last_wd['duration'] += first_phone['duration']

        if len(wd['phones']) > 1:
            if not (wd['phones'][0]['phone'].endswith('_B') or wd['phones'][0]['phone'].endswith('_S')):
                logging.info('Word does not start correctly, %s', str(wd))
                logging.info('previously: %s', str(last_wd))                
                # XXX: In this (rare!) case, I think getting rid of
                # the starting phoneme may be the right thing to do
                # (if, say, the second looks reasonable).
                #
                # I don't think this case should happen under normal
                # circumstance--it's only happening in debugging at
                # the beginning of the 20-second intervals.

            else:
                # Is the beginning of the next word here?
                for idx,ph in enumerate(wd['phones']):
                    if idx > 0 and ph['phone'].endswith('_B'):
                        next_phonemes = wd['phones'][idx:]
                        offset_duration = sum([X['duration'] for X in next_phonemes])
                        if offset_duration > max_offset:
                            logging.info("Skipping long offset adjustment (%d): %s", len(next_phonemes), str(wd))
                            next_phonemes = []
                            continue
                        wd['phones'] = wd['phones'][:idx]
                        wd['duration'] -= offset_duration
                        logging.info('Word contains the next beginning (%d)', idx)
                        break

        last_wd = wd

    # Strip silence from ends of words
    for wd in words:
        if len(wd['phones']) > 0 and wd['phones'][0]['phone'] == 'sil':
            p = wd['phones'].pop(0)
            wd['start'] += p['duration']
            wd['duration'] -= p['duration']

        if len(wd['phones']) > 0 and wd['phones'][-1]['phone'] == 'sil':
            p = wd['phones'].pop()
            wd['duration'] -= p['duration']

    return words

if __name__=='__main__':
    import json
    import sys
    logging.getLogger().setLevel(logging.DEBUG)
                         
    IN_JSON = sys.argv[1]
    OUT_JSON = sys.argv[2]

    inp = json.load(open(IN_JSON))

    words = [X for X in inp['words'] if X['case'] != 'not-found-in-audio']

    # ugh. normalize to start/duration
    for wd in words:
        wd['duration'] = wd['end'] - wd['start']
    
    words = tweak(words)

    # ...and back to start/end
    for wd in words:
        wd['end'] = wd['duration'] + wd['start']

    inp['words'] = words

    json.dump(inp, open(OUT_JSON, 'w'), indent=2)
