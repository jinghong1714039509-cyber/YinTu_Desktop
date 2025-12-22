import os
from pathlib import Path

# 应用基本信息
APP_NAME = "YinTu Desktop"
VERSION = "1.0.0"

# 路径配置
BASE_DIR = Path(os.getcwd())
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "yintu.db"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 业务配置
DEFAULT_FPS = 2  # 默认每秒抽2帧
SUPPORTED_VIDEO_EXT = ['.mp4', '.avi', '.mov', '.mkv']
SUPPORTED_IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.bmp']s