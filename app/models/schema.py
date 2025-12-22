from peewee import *
from datetime import datetime
from app.common.config import DB_PATH

db = SqliteDatabase(str(DB_PATH))

class BaseModel(Model):
    class Meta:
        database = db

class Project(BaseModel):
    name = CharField()
    path = CharField(unique=True)  # 项目根目录路径
    created_at = DateTimeField(default=datetime.now)
    description = TextField(null=True)

class MediaItem(BaseModel):
    project = ForeignKeyField(Project, backref='media')
    file_path = CharField()     # 图片的绝对路径
    media_type = CharField()    # 'image' 或 'extracted_frame'
    source_video = CharField(null=True) # 如果是抽帧，记录来源视频
    is_labeled = BooleanField(default=False)
    width = IntegerField(null=True)
    height = IntegerField(null=True)

class Annotation(BaseModel):
    media = ForeignKeyField(MediaItem, backref='annotations')
    label_class = CharField()   # 例如 'person', 'car'
    x_center = FloatField()     # YOLO 格式归一化坐标
    y_center = FloatField()
    width = FloatField()
    height = FloatField()
    confidence = FloatField(default=1.0)

def init_db():
    db.connect()
    db.create_tables([Project, MediaItem, Annotation])