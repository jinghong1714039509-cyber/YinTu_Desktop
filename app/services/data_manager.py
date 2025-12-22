import os
from pathlib import Path
from app.models.schema import Project, MediaItem, db
from app.common.config import SUPPORTED_IMAGE_EXT, SUPPORTED_VIDEO_EXT

class DataManager:
    @staticmethod
    def import_folder(folder_path):
        """扫描文件夹，入库，返回 (项目对象, 视频列表)"""
        folder_path = str(Path(folder_path).resolve())
        folder_name = os.path.basename(folder_path)

        # 1. 创建或获取项目
        project, created = Project.get_or_create(
            path=folder_path,
            defaults={'name': folder_name}
        )

        video_files = []
        new_media_count = 0

        # 2. 遍历文件
        with db.atomic(): # 开启事务，加速写入
            for root, dirs, files in os.walk(folder_path):
                # 忽略隐藏目录
                if any(part.startswith('.') for part in Path(root).parts):
                    continue

                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    full_path = os.path.join(root, file)

                    # 如果是图片
                    if ext in SUPPORTED_IMAGE_EXT:
                        MediaItem.get_or_create(
                            project=project,
                            file_path=full_path,
                            defaults={'media_type': 'image'}
                        )
                        new_media_count += 1
                    
                    # 如果是视频
                    elif ext in SUPPORTED_VIDEO_EXT:
                        MediaItem.get_or_create(
                            project=project,
                            file_path=full_path,
                            defaults={'media_type': 'video'}
                        )
                        video_files.append(full_path)

        return project, video_files, new_media_count

    @staticmethod
    def add_frames(project_id, frame_dir, source_video_path):
        """把抽帧生成的图片入库"""
        project = Project.get_by_id(project_id)
        frames = []
        for file in os.listdir(frame_dir):
            if file.lower().endswith('.jpg'):
                frames.append({
                    'project': project,
                    'file_path': os.path.join(frame_dir, file),
                    'media_type': 'frame',
                    'source_video': source_video_path
                })
        
        if frames:
            with db.atomic():
                MediaItem.insert_many(frames).execute()
        return len(frames)