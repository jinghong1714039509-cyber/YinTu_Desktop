from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QFrame, QProgressBar, QGridLayout)
from PySide6.QtCore import Qt, Signal
from app.services.data_manager import DataManager

class TaskCard(QFrame):
    """
    单个任务的卡片组件 (仿 AdminLTE Box)
    """
    enter_clicked = Signal(object) # 信号：点击了进入按钮，携带项目对象

    def __init__(self, project_data, parent=None):
        super().__init__(parent)
        self.data = project_data
        self.initUI()

    def initUI(self):
        # 卡片样式：白色背景，顶部有一条状态色的线，轻微阴影
        self.setFixedHeight(140)
        self.setStyleSheet(f"""
            TaskCard {{
                background-color: white;
                border-radius: 4px;
                border-top: 3px solid {self.data['status_color']};
                border-left: 1px solid #dee2e6;
                border-right: 1px solid #dee2e6;
                border-bottom: 1px solid #dee2e6;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # 1. 顶部：标题 + 状态标签
        top_layout = QHBoxLayout()
        
        title = QLabel(self.data['name'])
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        
        status_badge = QLabel(f" {self.data['status']} ")
        status_badge.setStyleSheet(f"""
            background-color: {self.data['status_color']}; 
            color: white; 
            border-radius: 4px; 
            padding: 2px 5px; 
            font-size: 12px; font-weight: bold;
        """)
        
        top_layout.addWidget(title)
        top_layout.addStretch(1)
        top_layout.addWidget(status_badge)
        layout.addLayout(top_layout)

        # 2. 中间：路径信息
        path_lbl = QLabel(f"📂 {self.data['path']}")
        path_lbl.setStyleSheet("color: #666; font-size: 13px; margin-bottom: 5px;")
        path_lbl.setWordWrap(True)
        layout.addWidget(path_lbl)

        # 3. 底部：进度条 + 按钮
        bottom_layout = QHBoxLayout()
        
        # 进度条区域
        progress_layout = QVBoxLayout()
        pg_info = QLabel(f"进度: {self.data['labeled']} / {self.data['total']}")
        pg_info.setStyleSheet("font-size: 12px; color: #888;")
        
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(self.data['progress'])
        progress.setFixedHeight(10)
        progress.setTextVisible(False)
        # 根据进度设置颜色
        progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background-color: #e9ecef; border-radius: 5px; }}
            QProgressBar::chunk {{ background-color: {self.data['status_color']}; border-radius: 5px; }}
        """)
        
        progress_layout.addWidget(pg_info)
        progress_layout.addWidget(progress)
        
        # 进入标注按钮
        btn_enter = QPushButton("✏️ 开始标注")
        btn_enter.setCursor(Qt.PointingHandCursor)
        btn_enter.setFixedSize(100, 35)
        btn_enter.setStyleSheet("""
            QPushButton {
                background-color: #007bff; color: white; border: none; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0056b3; }
        """)
        btn_enter.clicked.connect(lambda: self.enter_clicked.emit(self.data['object']))

        bottom_layout.addLayout(progress_layout)
        bottom_layout.addSpacing(20)
        bottom_layout.addWidget(btn_enter)
        
        layout.addLayout(bottom_layout)


class TaskListInterface(QWidget):
    project_selected = Signal(object) # 选中项目信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 0)
        
        # 标题
        header = QLabel("任务列表 / Task List")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #444; margin-bottom: 20px;")
        main_layout.addWidget(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: transparent;")
        self.card_layout = QVBoxLayout(self.scroll_content)
        self.card_layout.setSpacing(15)
        self.card_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.scroll_content)
        main_layout.addWidget(scroll)

    def refresh_data(self):
        """刷新列表数据"""
        # 清空旧卡片
        for i in reversed(range(self.card_layout.count())): 
            self.card_layout.itemAt(i).widget().setParent(None)

        # 获取数据
        projects = DataManager.get_all_projects_stats()
        
        if not projects:
            empty_lbl = QLabel("暂无任务，请先到“统计页”导入文件夹。")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: #888; font-size: 16px; margin-top: 50px;")
            self.card_layout.addWidget(empty_lbl)
            return

        # 生成卡片
        for p_data in projects:
            card = TaskCard(p_data)
            card.enter_clicked.connect(self.on_project_clicked)
            self.card_layout.addWidget(card)

    def on_project_clicked(self, project_obj):
        self.project_selected.emit(project_obj)