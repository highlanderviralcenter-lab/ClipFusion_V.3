import gc, subprocess, tempfile, os
from faster_whisper import WhisperModel
import db

class Transcriber:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def _load_model(self):
        if self.model is None:
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=4
            )

    def transcribe(self, audio_path, language=None):
        self._load_model()
        tmp = tempfile.mktemp(suffix=".wav")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1", tmp
            ], capture_output=True, check=True)
            segments_gen, info = self.model.transcribe(
                tmp,
                language=language,
                beam_size=5,
                best_of=5,
                condition_on_previous_text=True,
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250,
                    "max_speech_duration_s": 30,
                    "min_silence_duration_ms": 300
                },
                chunk_length=30
            )
            segments_list = [
                {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text}
                for s in segments_gen
            ]
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        return {
            "language": info.language,
            "segments": segments_list,
            "full_text": " ".join(s["text"] for s in segments_list),
        }

    def cleanup(self):
        del self.model
        self.model = None
        gc.collect()

def transcribe_project(project_id, video_path, model_size="small", language="pt"):
    transcriber = Transcriber(model_size=model_size)
    result = transcriber.transcribe(video_path, language=language)
    transcript_id = db.save_transcript(project_id, result["full_text"], result["segments"])
    transcriber.cleanup()
    return transcript_id, result
