from peewee import *
from datetime import datetime
from app.common.config import DB_PATH

# 连接 SQLite 数据库
db = SqliteDatabase(str(DB_PATH))

class BaseModel(Model):
    class Meta:
        database = db

class Project(BaseModel):
    name = CharField()
    path = CharField(unique=True)
    created_at = DateTimeField(default=datetime.now)

class MediaItem(BaseModel):
    project = ForeignKeyField(Project, backref='media')
    file_path = CharField()
    media_type = CharField() # 'image', 'video', 'frame'
    is_labeled = BooleanField(default=False)
    
    # 如果是抽帧生成的图片，记录它属于哪个视频
    source_video = CharField(null=True) 

# 初始化建表函数
def init_db():
    db.connect()
    db.create_tables([Project, MediaItem], safe=True)