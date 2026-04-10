def compute_quality_score(segments):
    if not segments:
        return 0.0
    total_words = sum(len(s['text'].split()) for s in segments)
    avg_words_per_segment = total_words / len(segments)
    score = min(avg_words_per_segment / 10.0, 1.0)
    return score

def filter_segments(segments, min_words=3):
    return [s for s in segments if len(s['text'].split()) >= min_words]
