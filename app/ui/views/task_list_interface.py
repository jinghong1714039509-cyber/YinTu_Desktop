import os
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
    delete_clicked = Signal(object) # 信号：删除

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
                border: 1px solid #ebeef5;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 20))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # 1. 顶部图标
        icon_lbl = QLabel()
        icon_lbl.setFixedHeight(70)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_path = os.path.join("app/assets/icons", "folder.svg")
        icon_lbl.setText("📁")
        icon_lbl.setStyleSheet("font-size: 38px; border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        # 2. 标题
        name_lbl = QLabel(self.data['name'])
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #303133; border: none; background: transparent;")
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
        status_lbl.setStyleSheet(f"color: {self.data['status_color']}; font-weight: 600; font-size: 13px; border: none; background: transparent;")
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

        btn_delete = QPushButton("删除")
        btn_delete.setFixedSize(60, 28)
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #dc3545;
                border-radius: 14px;
                color: #dc3545;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #ffecec; }
        """)
        btn_delete.clicked.connect(self.on_delete_btn_clicked) # 防止冒泡
        btn_layout.addWidget(btn_delete)

        layout.addLayout(btn_layout)

    def on_export_btn_clicked(self):
        """点击导出按钮时，只触发导出，不触发进入项目"""
        self.export_clicked.emit(self.data['object'])

    def on_delete_btn_clicked(self):
        """点击删除按钮时，只触发删除，不触发进入项目"""
        self.delete_clicked.emit(self.data['object'])

    # === 点击卡片任意位置进入项目（按钮点击不会触发这里） ===
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
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 顶部标题栏
        top_bar = QHBoxLayout()
        title = QLabel("任务列表")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #303133;")
        top_bar.addWidget(title)
        top_bar.addStretch(1)

        btn_new = QPushButton("新建任务")
        btn_new.setFixedSize(100, 34)
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: #fff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #0069d9; }
        """)
        btn_new.clicked.connect(self.open_new_task_dialog)
        top_bar.addWidget(btn_new)
        main_layout.addLayout(top_bar)

        # 滚动区 + 流式布局
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.flow_layout = FlowLayout(container, margin=0, spacing=18)
        container.setLayout(self.flow_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

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
            card.delete_clicked.connect(self.on_delete_clicked)
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
                
                # === 修复：使用白色背景的提示框 ===
                msg = QMessageBox(self)
                msg.setWindowTitle("导出成功")
                msg.setText(f"成功导出 {count} 张标注数据！\n格式: {data['format']}")
                msg.setStyleSheet("QMessageBox { background-color: white; color: #333; } QLabel { color: #333; }")
                msg.exec()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def on_delete_clicked(self, project_obj):
        # 删除前预览（统计将删除的数据量）
        try:
            preview = DataManager.preview_delete_project(project_obj)
            msg_text = (
                f"确认删除任务：{getattr(project_obj, 'name', '未命名')}\n\n"
                f"- 将删除图片索引：{preview.get('media_count', 0)} 条\n"
                f"- 将删除标注记录：{preview.get('annotation_count', 0)} 条\n\n"
                f"注意：默认不会删除你原始目录中的图片/视频文件。"
            )
        except Exception:
            msg_text = (
                f"确认删除任务：{getattr(project_obj, 'name', '未命名')}\n\n"
                "注意：默认不会删除你原始目录中的图片/视频文件。"
            )

        confirm = QMessageBox(self)
        confirm.setWindowTitle("确认删除")
        confirm.setText(msg_text)
        confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm.setDefaultButton(QMessageBox.No)
        confirm.setStyleSheet("QMessageBox { background-color: white; color: #333; } QLabel { color: #333; }")
        ret = confirm.exec()

        if ret != QMessageBox.Yes:
            return

        result = DataManager.delete_project(project_obj, delete_managed_files=False, delete_original_files=False)
        if not result.get("ok"):
            QMessageBox.critical(self, "删除失败", result.get("error") or "未知错误")
            return

        # 刷新任务列表
        self.refresh_data()

        done = QMessageBox(self)
        done.setWindowTitle("删除成功")
        deleted = result.get("deleted", {})
        done.setText(
            f"删除完成。\n"
            f"- Projects: {deleted.get('projects', 0)}\n"
            f"- MediaItems: {deleted.get('media', 0)}\n"
            f"- Annotations: {deleted.get('annotations', 0)}"
        )
        done.setStyleSheet("QMessageBox { background-color: white; color: #333; } QLabel { color: #333; }")
        done.exec()
