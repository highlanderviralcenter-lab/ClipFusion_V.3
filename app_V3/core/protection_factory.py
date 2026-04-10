"""Factory de proteção anti-copyright com 7 camadas."""

LAYER_ORDER = [
    "zoom_dinamico",          # 1
    "colorimetria_hardware",  # 2
    "strip_metadados",        # 3
    "reamostragem_audio",     # 4
    "ruido_sincrono",         # 5
    "ghost_mode_temporal",    # 6
    "horizontal_flip",        # 7
]


def layer_params(layer):
    params = {
        "zoom_dinamico": "scale=iw*1.02:ih*1.02,crop=iw:ih",
        "colorimetria_hardware": "eq=contrast=1.03:brightness=0.01:saturation=1.04",
        "strip_metadados": "-map_metadata -1 -map_chapters -1",
        "reamostragem_audio": "-af aresample=44100,atempo=1.0",
        "ruido_sincrono": "noise=alls=6:allf=t+u",
        "ghost_mode_temporal": "tblend=all_mode=average,framestep=1",
        "horizontal_flip": "hflip",
    }
    return params[layer]


def build_filter_chain(level="basic"):
    active = ["zoom_dinamico", "colorimetria_hardware"]
    if level in ("anti_ia", "maximum"):
        active += ["ruido_sincrono", "ghost_mode_temporal"]
    if level == "maximum":
        active += ["horizontal_flip"]
    return ",".join(layer_params(x) for x in active if x not in ("strip_metadados", "reamostragem_audio"))


def build_ffmpeg_args(level="basic"):
    vf = build_filter_chain(level)
    args = ["-vf", vf, "-af", "aresample=44100,atempo=1.0", "-map_metadata", "-1", "-map_chapters", "-1"]
    return args
