import sys
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