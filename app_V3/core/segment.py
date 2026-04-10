def segment_by_pauses(segments, min_duration=18, max_duration=35, pause_threshold=0.5):
    candidates = []
    current_start = None
    current_end = None
    current_text = []
    last_end = 0
    for seg in segments:
        if current_start is None:
            current_start = seg['start']
            current_end = seg['end']
            current_text = [seg['text']]
            last_end = seg['end']
            continue
        gap = seg['start'] - last_end
        if gap > pause_threshold or (seg['end'] - current_start) > max_duration:
            dur = current_end - current_start
            if dur >= min_duration:
                candidates.append({
                    'start': current_start,
                    'end': current_end,
                    'text': ' '.join(current_text)
                })
            current_start = seg['start']
            current_end = seg['end']
            current_text = [seg['text']]
        else:
            current_end = seg['end']
            current_text.append(seg['text'])
        last_end = seg['end']
    if current_start is not None and (current_end - current_start) >= min_duration:
        candidates.append({
            'start': current_start,
            'end': current_end,
            'text': ' '.join(current_text)
        })
    return candidates
