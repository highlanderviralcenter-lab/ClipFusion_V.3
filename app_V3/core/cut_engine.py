"""
Core — Cut Engine com render 2-pass correto para VA-API + legendas.

Passo 1: Corte + escala via VA-API h264_vaapi (rápido, sem legenda)
Passo 2: Burn legenda via libx264 (arquivo já pequeno = rápido também)
Se VA-API indisponível: 1 passo com libx264 + legenda.
"""
import subprocess, os, tempfile, shutil
from core.transcriber import fmt_time

PLATFORM_CONFIGS = {
    "tiktok":  {"w": 1080, "h": 1920, "max_dur": 180, "crf": 20,
                "preset": "fast", "fps": 30, "abr": "128k", "suffix": "_tiktok"},
    "reels":   {"w": 1080, "h": 1920, "max_dur": 90,  "crf": 21,
                "preset": "fast", "fps": 30, "abr": "128k", "suffix": "_reels"},
    "shorts":  {"w": 1080, "h": 1920, "max_dur": 60,  "crf": 21,
                "preset": "fast", "fps": 30, "abr": "128k", "suffix": "_shorts"},
}


def _ms(s: float) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{int((s%1)*1000):03d}"


def build_srt(segments: list, cut_start: float, cut_end: float) -> str:
    lines, idx = [], 1
    for seg in segments:
        if seg["end"] < cut_start or seg["start"] > cut_end:
            continue
        rs  = max(seg["start"] - cut_start, 0)
        re_ = min(seg["end"]   - cut_start, cut_end - cut_start)
        if re_ <= rs: continue
        lines += [str(idx), f"{_ms(rs)} --> {_ms(re_)}", seg["text"].strip(), ""]
        idx += 1
    return "\n".join(lines)


def _detect_vaapi() -> bool:
    try:
        r = subprocess.run(["vainfo"], capture_output=True, text=True)
        return "VAEntrypointEncSlice" in r.stdout
    except FileNotFoundError:
        return False


def render_cut(video_path: str, cut: dict, segments: list,
               output_dir: str, project_id: str,
               ace_level: str = "basic", use_vaapi: bool = True,
               progress_cb=None) -> dict:
    def log(m):
        if progress_cb: progress_cb(m)

    # FIX: Aceita tanto 'start'/'end' quanto 'start_time'/'end_time'
    start     = cut.get("start", cut.get("start_time", 0))
    end       = cut.get("end", cut.get("end_time", 0))
    duration  = end - start
    idx       = cut.get("cut_index", 0)
    platforms = cut.get("platforms", ["tiktok", "reels", "shorts"])
    safe_title = "".join(
        c for c in cut.get("title", f"corte_{idx}")
        if c.isalnum() or c in " _-"
    ).strip().replace(" ", "_")[:40]

    vaapi_ok = use_vaapi and _detect_vaapi()
    if use_vaapi and not vaapi_ok:
        log("  ⚠️  VA-API indisponível — usando libx264")

    tmp          = tempfile.mkdtemp()
    output_paths = {}

    try:
        srt_content = build_srt(segments, start, end)
        srt_path    = os.path.join(tmp, "sub.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        style = ("FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
                 "OutlineColour=&H00000000,Bold=1,Outline=2,Shadow=1,"
                 "Alignment=2,MarginV=60")

        for platform in platforms:
            cfg = PLATFORM_CONFIGS.get(platform)
            if not cfg: continue
            dur      = min(duration, cfg["max_dur"])
            w, h     = cfg["w"], cfg["h"]
            out_name = f"{safe_title}{cfg['suffix']}.mp4"
            out_path = os.path.join(output_dir, platform, out_name)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            log(f"  [{platform}] {out_name} ({fmt_time(dur)})")

            raw_out = os.path.join(tmp, f"raw_{platform}.mp4")
            ok      = False

            if vaapi_ok:
                # PASSO 1: hwaccel_device ANTES do -i, sem hwaccel_output_format
                cmd = [
                    "ffmpeg", "-y",
                    "-hwaccel", "vaapi",
                    "-hwaccel_device", "/dev/dri/renderD128",
                    "-ss", str(start), "-i", video_path, "-t", str(dur),
                    "-vf", (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
                            f"format=nv12,hwupload,scale_vaapi={w}:{h}"),
                    "-c:v", "h264_vaapi",
                    "-c:a", "aac", "-b:a", cfg["abr"], "-ar", "44100",
                    "-r", str(cfg["fps"]), "-movflags", "+faststart",
                    "-map_metadata", "-1", raw_out,
                ]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                ok = r.returncode == 0

                if ok and srt_content.strip():
                    # PASSO 2: Burn legenda em software (arquivo pequeno = rápido)
                    sub2 = os.path.join(tmp, f"sub_{platform}.mp4")
                    srt_esc = srt_path.replace("\\", "/").replace(":", "\\:")
                    cmd2 = [
                        "ffmpeg", "-y", "-i", raw_out,
                        "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
                        "-c:v", "libx264", "-preset", cfg["preset"], "-crf", str(cfg["crf"]),
                        "-c:a", "copy", "-r", str(cfg["fps"]), "-pix_fmt", "yuv420p",
                        sub2,
                    ]
                    r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=300)
                    if r2.returncode == 0:
                        raw_out = sub2

            if not ok:
                # FALLBACK: tudo em software (1 passo)
                scale = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black")
                if srt_content.strip():
                    srt_esc = srt_path.replace("\\", "/").replace(":", "\\:")
                    vf = f"{scale},subtitles='{srt_esc}':force_style='{style}'"
                else:
                    vf = scale
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start), "-i", video_path, "-t", str(dur),
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", cfg["preset"], "-crf", str(cfg["crf"]),
                    "-c:a", "aac", "-b:a", cfg["abr"], "-ar", "44100",
                    "-r", str(cfg["fps"]), "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", "-map_metadata", "-1", raw_out,
                ]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if r.returncode != 0:
                    log(f"  ❌ Render falhou: {r.stderr[-100:]}")
                    continue

            # Anti-copyright
            if ace_level != "none":
                from anti_copy_modules.core import (
                    AntiCopyrightEngine, ProtectionConfig, ProtectionLevel)
                lvl    = ProtectionLevel(ace_level)
                engine = AntiCopyrightEngine(project_id, idx,
                                             ProtectionConfig.from_level(lvl), log=log)
                engine.process(raw_out, out_path)
            else:
                shutil.copy2(raw_out, out_path)

            size = os.path.getsize(out_path) / (1024 * 1024)
            log(f"  ✅ {platform}: {size:.1f} MB")
            output_paths[platform] = out_path

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return output_paths


def render_all(video_path: str, cuts: list, segments: list,
               output_dir: str, project_id: str,
               ace_level: str = "basic", use_vaapi: bool = True,
               progress_cb=None) -> dict:
    import gc
    results = {}
    for i, cut in enumerate(cuts):
        if progress_cb:
            progress_cb(f"\n[{i+1}/{len(cuts)}] {cut.get('title','Corte')}")
        paths = render_cut(video_path, cut, segments, output_dir,
                           project_id, ace_level, use_vaapi, progress_cb)
        results[cut.get("id", cut.get("cut_index", i))] = paths
        gc.collect()  # GC explícito entre cortes (8GB RAM)
    return results
