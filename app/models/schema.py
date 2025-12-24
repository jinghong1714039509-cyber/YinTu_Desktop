from __future__ import annotations

from datetime import datetime
from peewee import (
    Model, SqliteDatabase,
    CharField, DateTimeField, TextField,
    ForeignKeyField, IntegerField, FloatField
)

from app.common.config import DB_PATH

db = SqliteDatabase(str(DB_PATH))


class BaseModel(Model):
    class Meta:
        database = db


class Project(BaseModel):
    """一个项目对应一个数据目录（图片/视频）。"""
    name = CharField()
    path = CharField(unique=True)  # 项目根目录路径
    created_at = DateTimeField(default=datetime.now)
    description = TextField(null=True)


class MediaItem(BaseModel):
    """一个媒体文件即一个标注任务（task）。"""
    project = ForeignKeyField(Project, backref='media', on_delete='CASCADE')
    file_path = CharField()               # 图片的绝对路径
    media_type = CharField(default='image')   # 'image' 或 'extracted_frame'
    source_video = CharField(null=True)   # 如果是抽帧，记录来源视频

    # 任务状态：0=未标注 1=标注中 2=已标注
    label_status = IntegerField(default=0)

    width = IntegerField(null=True)
    height = IntegerField(null=True)

    class Meta:
        indexes = (
            (('project', 'file_path'), True),  # (project, file_path) 唯一，避免重复导入
        )


class Annotation(BaseModel):
    media = ForeignKeyField(MediaItem, backref='annotations', on_delete='CASCADE')
    label_class = CharField()   # 例如 'person', 'car'
    x_center = FloatField()     # YOLO 格式归一化坐标
    y_center = FloatField()
    width = FloatField()
    height = FloatField()
    confidence = FloatField(default=1.0)


def _column_exists(table_name: str, column_name: str) -> bool:
    rows = db.execute_sql(f'PRAGMA table_info("{table_name}")').fetchall()
    cols = [r[1] for r in rows]  # r[1] = column name
    return column_name in cols


def _add_column_if_missing(model: type[Model], column_name: str, ddl: str) -> None:
    """轻量级迁移：仅在缺列时 ALTER TABLE。"""
    table = model._meta.table_name
    if not _column_exists(table, column_name):
        db.execute_sql(f'ALTER TABLE "{table}" ADD COLUMN {column_name} {ddl}')


def init_db() -> None:
    db.connect(reuse_if_open=True)
    db.create_tables([Project, MediaItem, Annotation])

    # 兼容旧库：补齐 label_status 字段
    _add_column_if_missing(MediaItem, 'label_status', 'INTEGER DEFAULT 0')
