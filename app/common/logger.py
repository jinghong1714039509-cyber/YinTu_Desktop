import logging
import sys
from app.common.config import LOG_DIR

def setup_logger():
    logger = logging.getLogger("YinTu")
    logger.setLevel(logging.DEBUG)

    # 格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出
    file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()