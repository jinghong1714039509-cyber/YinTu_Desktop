import sys
import os

# =========================================================================
# ☢️ 核弹级修复：强制屏蔽 PyQt5
# 既然卸载不掉，我们就假装它不存在。这会强迫所有库只能使用 PySide6。
# =========================================================================
sys.modules["PyQt5"] = None
sys.modules["PyQt5.QtCore"] = None
sys.modules["PyQt5.QtGui"] = None
sys.modules["PyQt5.QtWidgets"] = None

# 设置环境变量 (双重保险)
os.environ["QT_API"] = "pyside6"
os.environ["QT_FONT_DPI"] = "96"

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.models.schema import init_db

if __name__ == '__main__':
    # 1. 初始化数据库
    init_db()

    # 2. 启动应用
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    
    sys.exit(app.exec())