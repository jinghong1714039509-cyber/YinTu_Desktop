from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict

from peewee import IntegrityError

from app.common.config import SUPPORTED_IMAGE_EXT, SUPPORTED_VIDEO_EXT
from app.models.schema import Project, MediaItem, Annotation


class DataManager:
    """数据访问 + 导入同步层。

    约定：一个 MediaItem 即一个“任务(Task)”。
    label_status:
      0 = 未标注
      1 = 标注中
      2 = 已标注
    """

    STATUS_UNLABELED = 0
    STATUS_IN_PROGRESS = 1
    STATUS_DONE = 2

    @staticmethod
    def get_or_create_project(path: str, desc: str = "") -> Project:
        p = Path(path).resolve()
        name = p.name
        proj, created = Project.get_or_create(path=str(p), defaults={"name": name, "description": desc})
        if (not created) and (not proj.name):
            proj.name = name
            proj.save()
        return proj

    @staticmethod
    def get_all_projects() -> List[Project]:
        return list(Project.select().order_by(Project.created_at.desc()))

    @staticmethod
    def sync_media_from_folder(project: Project, folder: str) -> int:
        """扫描目录，把图片导入为任务（去重）。

        返回：新增的任务数量。
        """
        root = Path(folder).resolve()
        if not root.exists():
            return 0

        added = 0
        # 递归导入图片；视频先识别出来，后续接 worker 抽帧
        for fp in root.rglob('*'):
            if not fp.is_file():
                continue
            ext = fp.suffix.lower()

            if ext in SUPPORTED_IMAGE_EXT:
                try:
                    MediaItem.create(
                        project=project,
                        file_path=str(fp),
                        media_type='image',
                        source_video=None,
                        label_status=DataManager.STATUS_UNLABELED
                    )
                    added += 1
                except IntegrityError:
                    # 已存在（由 (project, file_path) 唯一索引保障）
                    pass

            # 如果未来要支持“导入视频 -> 自动抽帧”，这里可以把视频入库，
            # 再交给 VideoWorker 抽帧并写入 MediaItem(media_type='extracted_frame')。
            elif ext in SUPPORTED_VIDEO_EXT:
                # 暂时不做抽帧入库，避免阻塞 UI；你确认需求后我再把 worker 串起来
                pass

        return added

    @staticmethod
    def get_project_media(project_id: int, status: Optional[int] = None) -> List[MediaItem]:
        q = MediaItem.select().where(MediaItem.project == project_id).order_by(MediaItem.id.desc())
        if status is not None:
            q = q.where(MediaItem.label_status == status)
        return list(q)

    @staticmethod
    def get_task_stats(project_id: int) -> Dict[str, int]:
        base = MediaItem.select().where(MediaItem.project == project_id)
        total = base.count()
        unlabeled = base.where(MediaItem.label_status == DataManager.STATUS_UNLABELED).count()
        in_progress = base.where(MediaItem.label_status == DataManager.STATUS_IN_PROGRESS).count()
        done = base.where(MediaItem.label_status == DataManager.STATUS_DONE).count()
        return {
            "total": total,
            "unlabeled": unlabeled,
            "in_progress": in_progress,
            "done": done,
        }

    @staticmethod
    def set_task_status(media_id: int, status: int) -> None:
        MediaItem.update(label_status=status).where(MediaItem.id == media_id).execute()

    @staticmethod
    def save_annotation(media_id: int, label: str, x: float, y: float, w: float, h: float, conf: float = 1.0) -> Annotation:
        return Annotation.create(
            media=media_id,
            label_class=label,
            x_center=x, y_center=y, width=w, height=h,
            confidence=conf
        )

    @staticmethod
    def clear_annotations(media_id: int) -> None:
        Annotation.delete().where(Annotation.media == media_id).execute()
