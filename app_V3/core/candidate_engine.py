"""Micro-segmentação 18-35s por pausas naturais."""

from .segment import segment_by_pauses


def generate_candidates(project_id, transcript_id, segments, db_module, min_dur=18, max_dur=35, pause_threshold=0.5):
    windows = segment_by_pauses(
        segments,
        min_duration=min_dur,
        max_duration=max_dur,
        pause_threshold=pause_threshold,
    )
    ids = []
    for cand in windows:
        cid = db_module.save_candidate(
            project_id,
            transcript_id,
            cand["start"],
            cand["end"],
            cand["text"],
            scores={},
        )
        ids.append(cid)
    return ids
