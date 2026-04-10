class ScoringEngine:
    """Regra de Ouro do SignalCut Hybrid."""

    @staticmethod
    def combine(local_score, external_score, platform_fit, duration_fit, transcription_quality):
        final_score = (
            float(local_score) * 0.50
            + float(external_score) * 0.30
            + float(platform_fit) * 0.10
            + float(duration_fit) * 0.05
            + float(transcription_quality) * 0.05
        )
        return round(final_score, 2)

    @staticmethod
    def classify(final_score):
        if final_score >= 9.0:
            return "Aprovado"
        if final_score >= 7.0:
            return "Rework"
        return "Descartado"

    def score_with_verdict(self, local_score, external_score, platform_fit, duration_fit, transcription_quality):
        score = self.combine(local_score, external_score, platform_fit, duration_fit, transcription_quality)
        return {
            "combined_score": score,
            "decision": self.classify(score),
        }
