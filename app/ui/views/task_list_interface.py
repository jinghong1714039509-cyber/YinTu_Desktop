from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QScrollArea, QFrame, QProgressBar, QMessageBox,
                               QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath

from app.services.data_manager import DataManager
from app.ui.components.export_dialog import ExportDialog
from app.ui.components.flow_layout import FlowLayout
from app.ui.views.home_interface import NewProjectDialog

# === 现代风格任务卡片 ===
class TaskCard(QFrame):
    enter_clicked = Signal(object)  # 信号：进入项目
    export_clicked = Signal(object) # 信号：导出

    def __init__(self, project_data, parent=None):
        super().__init__(parent)
        self.data = project_data
        self.setFixedSize(240, 280)
        self.setCursor(Qt.PointingHandCursor)
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            TaskCard {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #eef1f6;
            }
            TaskCard:hover {
                border: 1px solid #007bff; /* 悬停时边框变蓝 */
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 15))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 30, 25, 25)
        layout.setSpacing(15)

        # 1. 图标
        icon_lbl = QLabel("📁")
        icon_lbl.setStyleSheet("font-size: 32px; border: none; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignLeft)
        layout.addWidget(icon_lbl)

        # 2. 任务名称
        name_lbl = QLabel(self.data['name'])
        name_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; border: none; background: transparent;")
        name_lbl.setWordWrap(True)
        layout.addWidget(name_lbl)
        
        # 3. 进度条
        progress_layout = QVBoxLayout()
        pg_info = QLabel(f"进度: {self.data['labeled']} / {self.data['total']}")
        pg_info.setStyleSheet("font-size: 12px; color: #909399; border: none; background: transparent;")
        
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(self.data['progress'])
        progress.setFixedHeight(6)
        progress.setTextVisible(False)
        pg_color = "#007bff"
        if self.data['status'] == '已完成': pg_color = "#28a745"
        elif self.data['status'] == '未标注': pg_color = "#dc3545"

        progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background-color: #f0f2f5; border-radius: 3px; }} 
            QProgressBar::chunk {{ background-color: {pg_color}; border-radius: 3px; }}
        """)
        progress_layout.addWidget(pg_info)
        progress_layout.addWidget(progress)
        layout.addLayout(progress_layout)

        layout.addStretch(1)

        # 4. 底部按钮行
        btn_layout = QHBoxLayout()
        status_lbl = QLabel(self.data['status'])
        status_lbl.setStyleSheet(f"color: {self.data['status_color']}; font-weight: bold; font-size: 13px; border: none; background: transparent;")
        btn_layout.addWidget(status_lbl)
        btn_layout.addStretch(1)

        btn_export = QPushButton("导出")
        btn_export.setFixedSize(60, 28)
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #007bff;
                border-radius: 14px;
                color: #007bff;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #e6f0ff; }
        """)
        btn_export.clicked.connect(self.on_export_btn_clicked) # 防止冒泡
        btn_layout.addWidget(btn_export)
        layout.addLayout(btn_layout)

    def on_export_btn_clicked(self):
        """点击导出按钮时，只触发导出，不触发进入项目"""
        self.export_clicked.emit(self.data['object'])

    # === 关键修复：点击卡片任意位置（除了导出按钮）进入项目 ===
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 简单的点击反馈动画
            anim = QPropertyAnimation(self, b"pos")
            anim.setDuration(100)
            anim.setStartValue(self.pos())
            anim.setEndValue(self.pos() + QPoint(2, 2))
            anim.setEasingCurve(QEasingCurve.OutQuad)
            anim.start()
            
            # 发射信号
            self.enter_clicked.emit(self.data['object'])
            
        super().mousePressEvent(event)


class TaskListInterface(QWidget):
    project_selected = Signal(object) 
    new_project_signal = Signal(dict) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        header_bar = QFrame()
        header_bar.setFixedHeight(70)
        header_bar.setStyleSheet("background-color: transparent; border-bottom: 1px solid #eef1f6;")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(40, 0, 40, 0)
        title = QLabel("我的任务")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #2c3e50;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addWidget(header_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f4f7f9; }") 
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #f4f7f9;") 
        
        self.flow_layout = FlowLayout(self.scroll_content, margin=40, spacing=30)
        
        scroll.setWidget(self.scroll_content)
        main_layout.addWidget(scroll)

        # 悬浮按钮
        self.fab_btn = QPushButton(self)
        self.fab_btn.setText("+") 
        self.fab_btn.setFixedSize(56, 56)
        self.fab_btn.setCursor(Qt.PointingHandCursor)
        self.fab_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff; 
                color: white;
                font-size: 36px;
                font-weight: 300;
                border-radius: 28px;
                border: none;
                padding-bottom: 4px; 
            }
            QPushButton:hover { background-color: #0069d9; }
            QPushButton:pressed { background-color: #0056b3; }
        """)
        
        fab_shadow = QGraphicsDropShadowEffect(self.fab_btn)
        fab_shadow.setBlurRadius(15)
        fab_shadow.setColor(QColor(0,0,0,100))
        fab_shadow.setYOffset(6)
        self.fab_btn.setGraphicsEffect(fab_shadow)
        
        self.fab_btn.clicked.connect(self.open_new_task_dialog)
        self.fab_btn.raise_() 

    def resizeEvent(self, event):
        super().resizeEvent(event)
        fab_x = self.width() - self.fab_btn.width() - 40
        fab_y = self.height() - self.fab_btn.height() - 40
        self.fab_btn.move(fab_x, fab_y)

    def refresh_data(self):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        projects = DataManager.get_all_projects_stats()
        if not projects: return

        for p_data in projects:
            card = TaskCard(p_data)
            # 连接信号
            card.enter_clicked.connect(self.on_project_clicked)
            card.export_clicked.connect(self.on_export_clicked)
            self.flow_layout.addWidget(card)

    def open_new_task_dialog(self):
        dialog = NewProjectDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if data['folder']:
                self.new_project_signal.emit(data)

    def on_project_clicked(self, project_obj):
        self.project_selected.emit(project_obj)

    def on_export_clicked(self, project_obj):
        dialog = ExportDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                count = DataManager.export_dataset(project_obj, data['path'], data['format'])
                QMessageBox.information(self, "成功", f"导出完成！共 {count} 张")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))