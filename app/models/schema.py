from peewee import *
from app.common.config import DB_PATH
import datetime

db = SqliteDatabase(DB_PATH)

class BaseModel(Model):
    class Meta:
        database = db

class Project(BaseModel):
    name = CharField()
    path = CharField(unique=True)
    description = TextField(null=True)
    model_path = CharField(null=True)
    classes = TextField(null=True) 
    created_at = DateTimeField(default=datetime.datetime.now)

class MediaItem(BaseModel):
    project = ForeignKeyField(Project, backref='media')
    file_path = CharField()
    media_type = CharField(default='image') 
    is_labeled = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)

class Annotation(BaseModel):
    media_item = ForeignKeyField(MediaItem, backref='annotations')
    label = CharField()
    
    # 矩形框数据 (归一化 cx, cy, w, h) - 即使是多边形也算一个包围盒存这里
    x = FloatField(default=0)
    y = FloatField(default=0)
    w = FloatField(default=0)
    h = FloatField(default=0)
    
    # 新增：形状类型 (rect / polygon)
    shape_type = CharField(default='rect') 
    
    # 新增：多边形点集 (存 JSON 字符串: "[[0.1, 0.2], [0.3, 0.4]]")
    points = TextField(null=True) 
    
    confidence = FloatField(default=1.0)
    created_at = DateTimeField(default=datetime.datetime.now)

def init_db():
    db.connect()
    db.create_tables([Project, MediaItem, Annotation])