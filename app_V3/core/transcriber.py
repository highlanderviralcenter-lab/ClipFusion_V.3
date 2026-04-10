"""Core — Transcrição Whisper via Python API."""
import os, tempfile, shutil, subprocess, gc


def fmt_time(s: float) -> str:
    return f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"


class WhisperTranscriber:
    def __init__(self, model: str = "tiny", language: str = "pt"):
        self.model = model
        self.language = language
        try:
            import whisper
            self._whisper = whisper
        except ImportError:
            raise RuntimeError("Whisper não instalado. Execute: pip install openai-whisper")

    def transcribe(self, video_path: str, progress_callback=None) -> dict:
        def log(msg):
            if progress_callback: progress_callback(msg)
            print(msg)

        tmp_dir  = tempfile.mkdtemp()
        wav_path = os.path.join(tmp_dir, "audio.wav")
        try:
            log("🔊 Extraindo áudio (16kHz mono)...")
            r = subprocess.run([
                'ffmpeg', '-y', '-i', video_path,
                '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', wav_path
            ], capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"FFmpeg erro: {r.stderr[-200:]}")

            log(f"🧠 Transcrevendo com Whisper '{self.model}'...")
            model = self._whisper.load_model(self.model, device="cpu")
            result = model.transcribe(
                wav_path, language=self.language, fp16=False,
                condition_on_previous_text=True, verbose=False,
                no_speech_threshold=0.6, logprob_threshold=-1.0,
            )
            del model; gc.collect()

            segments = [
                {'start': round(s['start'], 2), 'end': round(s['end'], 2),
                 'text':  s['text'].strip()}
                for s in result.get('segments', [])
            ]
            log(f"✅ {len(segments)} segmentos transcritos.")
            return {
                'full_text': ' '.join(s['text'] for s in segments),
                'segments':  segments,
                'language':  result.get('language', self.language),
            }
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def transcribe(video_path: str, model: str = "tiny",
               language: str = "pt", progress_cb=None) -> dict:
    return WhisperTranscriber(model, language).transcribe(video_path, progress_cb)
