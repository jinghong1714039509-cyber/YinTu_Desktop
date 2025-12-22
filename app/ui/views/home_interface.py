from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PySide6.QtCore import Qt, Signal

class HomeInterface(QWidget):
    # 定义一个信号：当用户选好文件夹后，把路径发出去
    project_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        # 1. 布局管理
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter) # 居中对齐
        layout.setSpacing(20) # 控件间距

        # 2. 标题
        self.title_label = QLabel("欢迎使用 YinTu 智能标注系统")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        self.title_label.setAlignment(Qt.AlignCenter)

        # 3. 说明文字
        self.desc_label = QLabel("请导入包含视频或图片的文件夹以开始项目")
        self.desc_label.setStyleSheet("font-size: 14px; color: #666;")
        self.desc_label.setAlignment(Qt.AlignCenter)

        # 4. 导入按钮
        self.import_btn = QPushButton("打开/创建项目文件夹")
        self.import_btn.setFixedSize(200, 50)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1084d9;
            }
        """)
        self.import_btn.clicked.connect(self.open_folder)

        # 5. 添加到布局
        layout.addStretch(1) # 上方弹簧
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.import_btn)
        layout.addStretch(1) # 下方弹簧

    def open_folder(self):
        # 调出原生的文件选择框
        folder_path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        
        if folder_path:
            # 如果用户选了路径，就发射信号
            print(f"用户选择了路径: {folder_path}") # 控制台打印一下
            self.project_selected.emit(folder_path)