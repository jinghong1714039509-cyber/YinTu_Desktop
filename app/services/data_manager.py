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
class DataManager:
    # ... (之前的 import_folder, add_frames 方法保持不变，不要删除) ...

    @staticmethod
    def get_all_projects_stats():
        """
        获取所有项目及其统计信息
        返回格式: List[Dict]
        """
        stats_list = []
        projects = Project.select().order_by(Project.created_at.desc())
        
        for p in projects:
            # 统计图片总数
            total_count = MediaItem.select().where(MediaItem.project == p).count()
            
            # 统计已标注数 (这里假设有 Annotation 记录的图片就算已标注，或者根据 is_labeled 字段)
            # 为了更准，我们查询 MediaItem 中 is_labeled=True 的数量
            labeled_count = MediaItem.select().where(
                (MediaItem.project == p) & (MediaItem.is_labeled == True)
            ).count()
            
            # 确定状态
            if total_count == 0:
                status = "空项目"
                status_color = "#6c757d" # Grey
            elif labeled_count == 0:
                status = "未标注"
                status_color = "#dc3545" # Red
            elif labeled_count < total_count:
                status = "标注中"
                status_color = "#ffc107" # Yellow
            else:
                status = "已完成"
                status_color = "#28a745" # Green

            stats_list.append({
                'id': p.id,
                'object': p, # 数据库对象
                'name': p.name,
                'path': p.path,
                'total': total_count,
                'labeled': labeled_count,
                'progress': int((labeled_count / total_count) * 100) if total_count > 0 else 0,
                'status': status,
                'status_color': status_color
            })
            
        return stats_list