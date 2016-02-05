import logging

def tweak(tokens, max_phone_offset=99):
    # Strip silence from ends of words
    for token in tokens:
        if len(token['phones']) > 0 and token['phones'][0]['phone'] == 'sil':
            phone = token['phones'].pop(0)
            token['time']['start'] += phone['duration']
            token['time']['duration'] -= phone['duration']

        if len(token['phones']) > 0 and token['phones'][-1]['phone'] == 'sil':
            phone = token['phones'].pop()
            token['time']['duration'] -= phone['duration']
    
    # Move mis-aligned phones
    last_token = None
    next_phones = []
    for token in tokens:
        if len(next_phones) > 0:
            # Add the previous phones
            duration = sum([phone['duration'] for X in next_phones])

            # Merge if the edge is identical
            if len(token['phones']) > 0 and next_phones[-1]['phone'] == token['phones'][0]['phone']:
                token['phones'][0]['duration'] += next_phones[-1]['duration']
                next_phones = next_phones[:-1]

            token['phones'] = next_phones + token['phones']
            token['time']['start'] -= duration
            token['time']['duration'] += duration

            next_phones = []

        # Did we get the end of the last word
        elif len(token['phones']) >= 1 \
             and last_token is not None \
             and token['phones'][0]['phone'][-1] in 'ES' \
             and (len(last_token['phones']) == 0 or \
                  (not last_token['phones'][-1]['phone'].endswith('_E')) \
                   or last_token['phones'][-1]['phone'] == token['phones'][0]['phone']):
            
            first_phone = token['phones'][0]
            token['phones'] = token['phones'][1:]
            token['time']['duration'] -= first_phone['duration']
            token['time']['start'] += first_phone['duration']

            if len(last_token['phones']) > 0 and last_token['phones'][-1]['phone'] == first_phone['phone']:
                last_token['phones'][-1]['duration'] += first_phone['duration']
            else:
                last_token['phones'].append(first_phone)
            last_token['time']['duration'] += first_phone['duration']

        if len(token['phones']) > 1:
            if not (token['phones'][0]['phone'].endswith('_B') or token['phones'][0]['phone'].endswith('_S')):
                logging.info('Word does not start correctly, %s', str(token))
                logging.info('previously: %s', str(last_token))                
                # XXX: In this (rare!) case, I think getting rid of
                # the starting phoneme may be the right thing to do
                # (if, say, the second looks reasonable).
                #
                # I don't think this case should happen under normal
                # circumstance--it's only happening in debugging at
                # the beginning of the 20-second intervals.

            else:
                # Is the beginning of the next word here?
                for idx, phone in enumerate(token['phones']):
                    if idx > 0 and phone['phone'].endswith('_B'):
                        next_phones = token['phones'][idx:]
                        if len(next_phones) > max_phone_offset:
                            logging.info("Skipping long offset adjustment (%d): %s", len(next_phones), str(token))
                            next_phones = []
                            continue
                        offset_duration = sum([phone['duration'] for phone in next_phones])
                        token['phones'] = token['phones'][:idx]
                        token['time']['duration'] -= offset_duration
                        logging.info('Word contains the next beginning (%d)', idx)
                        break

        last_token = token

    # Strip silence from ends of words
    for token in tokens:
        if len(token['phones']) > 0 and token['phones'][0]['phone'] == 'sil':
            phone = token['phones'].pop(0)
            token['time']['start'] += phone['duration']
            token['time']['duration'] -= phone['duration']

        if len(token['phones']) > 0 and token['phones'][-1]['phone'] == 'sil':
            phone = token['phones'].pop()
            token['time']['duration'] -= phone['duration']

    return tokens

if __name__=='__main__':
    import json
    import sys
    logging.getLogger().setLevel(logging.DEBUG)
                         
    IN_JSON = sys.argv[1]
    OUT_JSON = sys.argv[2]

    alignment = json.load(open(IN_JSON))

    tokens = [token for token in alignment['tokens'] if token['case'] != 'not-found-in-audio']
    tokens = tweak(tokens)
    alignment['tokens'] = tokens

    json.dump(inp, open(OUT_JSON, 'w'), indent=2)
