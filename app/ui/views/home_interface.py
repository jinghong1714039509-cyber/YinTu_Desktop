from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal
from app.ui.components.card import CardWidget

class HomeInterface(QWidget):
    project_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        # 整体背景色设置为淡灰色 (AdminLTE 风格背景)
        self.setStyleSheet("background-color: #f4f6f9;")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- 顶部欢迎语 ---
        welcome_label = QLabel("仪表盘 / Dashboard")
        welcome_label.setStyleSheet("font-size: 24px; color: #333; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(welcome_label)

        # --- 卡片区域布局 (水平排列) ---
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # === 卡片 1: 快速开始 ===
        card_start = CardWidget("🚀 快速开始", top_color="#007bff") # 蓝色顶条
        
        start_desc = QLabel("导入包含视频或图片的文件夹以开始新的标注任务。")
        start_desc.setWordWrap(True)
        start_desc.setStyleSheet("color: #666; font-size: 14px; margin-bottom: 15px; border: none;")
        
        self.import_btn = QPushButton("📂 打开/创建项目文件夹")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.setFixedHeight(40)
        # 扁平化按钮样式
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #0069d9; }
            QPushButton:pressed { background-color: #0062cc; }
        """)
        self.import_btn.clicked.connect(self.open_folder)

        card_start.add_widget(start_desc)
        card_start.add_widget(self.import_btn)
        
        # === 卡片 2: 系统状态 (示例) ===
        card_stat = CardWidget("📊 系统状态", top_color="#28a745") # 绿色顶条
        
        stat_label = QLabel("AI 模型引擎: YOLOv8\nGPU 加速: 检测中...\n当前版本: 1.0.0 Dev")
        stat_label.setStyleSheet("color: #555; line-height: 150%; font-size: 13px; border: none;")
        card_stat.add_widget(stat_label)

        # 将卡片加入布局
        cards_layout.addWidget(card_start, 2) # 权重2，宽一点
        cards_layout.addWidget(card_stat, 1)  # 权重1，窄一点
        
        main_layout.addLayout(cards_layout)
        main_layout.addStretch(1) # 下方留白

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if folder_path:
            self.project_selected.emit(folder_path)