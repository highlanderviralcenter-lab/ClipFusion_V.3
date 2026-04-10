"""ClipFusion — AI Evasion. Perturba embeddings CNN e motion vectors."""
import random

class AIEvasion:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def ffmpeg_filters(self) -> list:
        filters = []
        filters.append("vignette=angle=PI/5:mode=backward")
        jitter = self.rng.uniform(0.0001, 0.0003)
        filters.append(f"setpts=PTS+{jitter:.5f}*random(0)")
        sigma = self.rng.uniform(0.2, 0.4)
        filters.append(f"gblur=sigma={sigma:.2f}")
        return filters
