import os
import shutil
from pathlib import Path
from datetime import datetime
import db

def create_project_structure(project_name, video_path, base_workspace="./workspace/projects"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in project_name if c.isalnum() or c in " _-").strip().replace(" ", "_")
    project_dir = Path(base_workspace) / f"{safe_name}_{timestamp}"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "source").mkdir()
    (project_dir / "work").mkdir()
    (project_dir / "output").mkdir()
    (project_dir / "state").mkdir()
    src_video = Path(video_path)
    dest_video = project_dir / "source" / src_video.name
    shutil.copy2(src_video, dest_video)
    return str(project_dir), str(dest_video)

def ingest_video(project_name, video_path, language='pt'):
    project_dir, video_path_in_project = create_project_structure(project_name, video_path)
    project_id = db.create_project(project_name, video_path_in_project, language)
    return project_id, project_dir
