from app.models.schema import Project, MediaItem, Annotation, db

class DataManager:
    @staticmethod
    def create_project(name, path, desc=""):
        return Project.create(name=name, path=path, description=desc)

    @staticmethod
    def get_all_projects():
        return list(Project.select().order_by(Project.created_at.desc()))

    @staticmethod
    def add_media_item(project_id, file_path, m_type='image', source=None, w=0, h=0):
        return MediaItem.create(
            project=project_id,
            file_path=file_path,
            media_type=m_type,
            source_video=source,
            width=w,
            height=h
        )

    @staticmethod
    def get_project_media(project_id):
        return list(MediaItem.select().where(MediaItem.project == project_id))

    @staticmethod
    def save_annotation(media_id, label, x, y, w, h, conf=1.0):
        return Annotation.create(
            media=media_id, label_class=label,
            x_center=x, y_center=y, width=w, height=h, confidence=conf
        )
        
    @staticmethod
    def clear_annotations(media_id):
        Annotation.delete().where(Annotation.media == media_id).execute()