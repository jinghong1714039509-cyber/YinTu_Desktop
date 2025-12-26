from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QFrame, QGridLayout, 
                               QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
                               QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from app.services.data_manager import DataManager

# === 现代风格的新建项目对话框 ===
# ... (前面的导入保持不变)

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新任务")
        self.setFixedSize(480, 350)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { font-size: 14px; color: #555; }
            QLineEdit { 
                padding: 10px; border: 1px solid #e0e0e0; border-radius: 6px; background: #f9f9f9; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #007bff; background: #fff; }
            QPushButton {
                padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 6px; background: #f0f2f5; color: #555;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        self.folder_path = ""
        self.model_path = ""
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        title_lbl = QLabel("填写任务信息")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title_lbl)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignRight)
        
        # 1. 任务名称
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("任务名称（可选）")
        form.addRow("名称:", self.input_name)

        # 2. 文件路径 (修改点：增加选择视频按钮)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("选择文件夹或视频...")
        
        btn_folder = QPushButton("📁 文件夹")
        btn_folder.setToolTip("选择图片文件夹")
        btn_folder.clicked.connect(self.select_folder)
        
        btn_video = QPushButton("🎬 视频")
        btn_video.setToolTip("选择单个视频文件")
        btn_video.clicked.connect(self.select_video)
        
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_folder)
        path_layout.addWidget(btn_video)
        form.addRow("数据源:", path_layout)

        # 3. 选择模型
        model_layout = QHBoxLayout()
        self.model_edit = QLineEdit()
        self.model_edit.setReadOnly(True)
        self.model_edit.setPlaceholderText("默认 (yolov8n.pt)")
        btn_model = QPushButton("选择...")
        btn_model.clicked.connect(self.select_model)
        model_layout.addWidget(self.model_edit)
        model_layout.addWidget(btn_model)
        form.addRow("模型:", model_layout)

        # 4. 添加标签
        self.input_classes = QLineEdit()
        self.input_classes.setPlaceholderText("例如: person, car")
        form.addRow("标签:", self.input_classes)

        layout.addLayout(form)
        layout.addStretch(1)

        # 按钮
        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("立即创建")
        btn_ok.setStyleSheet("background: #007bff; color: white; border: none; font-weight: bold;")
        btn_ok.clicked.connect(self.accept)
        
        btn_box.addWidget(btn_cancel)
        btn_box.addSpacing(10)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)

    def select_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if d:
            self.folder_path = d
            self.path_edit.setText(d)
            if not self.input_name.text():
                import os
                self.input_name.setText(os.path.basename(d))

    # 新增：选择视频文件
    def select_video(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
        if f:
            self.folder_path = f
            self.path_edit.setText(f)
            if not self.input_name.text():
                import os
                self.input_name.setText(os.path.basename(f))

    def select_model(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择模型", "", "YOLO Models (*.pt)")
        if f:
            self.model_path = f
            import os
            self.model_edit.setText(os.path.basename(f))

    def get_data(self):
        return {
            'name': self.input_name.text().strip(),
            'folder': self.folder_path,
            'model': self.model_path if self.model_path else None,
            'classes': self.input_classes.text().strip()
        }
# ...
# ... (StatCard 和 HomeInterface 的其余部分不需要变，为了简洁这里省略) ...

# === 统计卡片 (保持不变) ===
class StatCard(QFrame):
    def __init__(self, title, value, icon, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"StatCard {{ background-color: white; border-radius: 4px; border: 1px solid #dee2e6; }}")
        self.setFixedHeight(90)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        icon_box = QLabel(icon)
        icon_box.setFixedWidth(90)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(f"background-color: {color}; color: white; font-size: 30px; border-top-left-radius: 4px; border-bottom-left-radius: 4px;")
        
        text_box = QWidget()
        text_layout = QVBoxLayout(text_box)
        text_layout.setAlignment(Qt.AlignVCenter)
        text_layout.setContentsMargins(15, 0, 0, 0)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #666; font-size: 13px; text-transform: uppercase;")
        lbl_value = QLabel(str(value))
        lbl_value.setStyleSheet("color: #333; font-size: 20px; font-weight: bold;")
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_value)
        layout.addWidget(icon_box)
        layout.addWidget(text_box)
        layout.addStretch(1)

# === 首页主类 ===
class HomeInterface(QWidget):
    project_selected = Signal(dict) # 修改信号类型：传字典

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        title_box = QHBoxLayout()
        title = QLabel("仪表盘 / Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #444;")
        title_box.addWidget(title)
        title_box.addStretch(1)
        
        self.importBtn = QPushButton("📂 新建/导入项目")
        self.importBtn.setCursor(Qt.PointingHandCursor)
        self.importBtn.setFixedSize(160, 40)
        self.importBtn.setStyleSheet("QPushButton { background-color: #007bff; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 14px; } QPushButton:hover { background-color: #0069d9; }")
        self.importBtn.clicked.connect(self.open_dialog)
        title_box.addWidget(self.importBtn)
        
        main_layout.addLayout(title_box)

        self.stats_layout = QGridLayout()
        self.stats_layout.setSpacing(20)
        main_layout.addLayout(self.stats_layout)
        self.refresh_stats()
        main_layout.addStretch(1)

    def refresh_stats(self):
        for i in reversed(range(self.stats_layout.count())): 
            self.stats_layout.itemAt(i).widget().setParent(None)

        projects = DataManager.get_all_projects_stats()
        total_projects = len(projects)
        total_images = sum(p['total'] for p in projects)
        total_labeled = sum(p['labeled'] for p in projects)
        rate = int((total_labeled / total_images * 100)) if total_images > 0 else 0

        self.stats_layout.addWidget(StatCard("总项目数", total_projects, "📁", "#17a2b8"), 0, 0)
        self.stats_layout.addWidget(StatCard("图片总数", total_images, "🖼️", "#28a745"), 0, 1)
        self.stats_layout.addWidget(StatCard("已标注", total_labeled, "🏷️", "#ffc107"), 0, 2)
        self.stats_layout.addWidget(StatCard("完成率", f"{rate}%", "📈", "#dc3545"), 0, 3)

    def open_dialog(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data['folder']:
                self.project_selected.emit(data) # 发送完整配置
    
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_stats()