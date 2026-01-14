import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QStackedWidget, QMessageBox, QProgressDialog, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication

from app.ui.components.sidebar import Sidebar
from app.ui.components.header import Header
from app.ui.views.home_interface import HomeInterface
from app.ui.views.label_interface import LabelInterface
from app.ui.views.task_list_interface import TaskListInterface
from app.services.data_manager import DataManager
from app.workers.video_worker import VideoExtractWorker
from app.workers.ai_worker import AiWorker
from app.common.config import DATA_DIR
from app.models.schema import MediaItem

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YinTu Desktop Pro")
        self.resize(1360, 800)
        self.center_window()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # === 修复重点：全局亮色主题 + 强制修复弹窗黑屏 ===
        self.setStyleSheet("""
            /* 全局背景设为白色 */
            QMainWindow, QWidget#CentralWidget {
                background-color: #FFFFFF; 
                border-radius: 12px;
                border: 1px solid #CCCCCC;
            }
            /* 所有 Label 默认深色字 */
            QLabel { color: #333333; font-family: 'Microsoft YaHei', 'Segoe UI'; }
            
            /* === 核心修复：防止弹窗(QDialog)黑屏 === */
            QDialog {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #CCC;
            }
            /* 修复输入框看不见字 */
            QLineEdit {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #CCC;
                padding: 5px;
                border-radius: 4px;
            }
            /* 修复列表背景和选中色 */
            QListWidget {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #DDD;
                outline: none;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected {
                background-color: #3B82F6; /* 选中变蓝 */
                color: #FFFFFF;
            }
            QListWidget::item:hover {
                background-color: #F0F0F0;
                color: #000000;
            }
            /* 修复按钮样式 */
            QPushButton {
                background-color: #F0F0F0;
                color: #333;
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #E0E0E0; }
            QPushButton:pressed { background-color: #D0D0D0; }
        """)

        # 核心容器
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)
        
        # 阴影变浅
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 40)) 
        self.central_widget.setGraphicsEffect(shadow)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 左侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        self.main_layout.addWidget(self.sidebar)

        # 右侧内容区
        self.content_container = QWidget()
        # 右侧背景微灰，区分层次
        self.content_container.setStyleSheet("background-color: #FAFAFA; border-top-right-radius: 12px; border-bottom-right-radius: 12px;")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Header 样式适配白色
        self.header = Header()
        self.header.setStyleSheet("""
            QFrame { background-color: transparent; border-bottom: 1px solid #E0E0E0; }
            QLabel { color: #333; font-weight: bold; }
            QPushButton { color: #666; border: none; background: transparent; }
            QPushButton:hover { background-color: #E0E0E0; color: #000; }
        """)
        self.header.close_clicked.connect(self.close)
        self.header.min_clicked.connect(self.showMinimized)
        self.header.max_clicked.connect(self.toggle_maximize)
        self.header.mouseMoveEvent = self.moveWindow
        self.header.mousePressEvent = self.pressWindow
        self.content_layout.addWidget(self.header)

        # 页面堆栈
        self.stack = QStackedWidget()
        self.home_interface = HomeInterface()          
        self.task_list_interface = TaskListInterface() 
        self.label_interface = LabelInterface()        
        
        self.stack.addWidget(self.home_interface)
        self.stack.addWidget(self.task_list_interface)
        self.stack.addWidget(self.label_interface)
        
        self.content_layout.addWidget(self.stack)
        self.main_layout.addWidget(self.content_container)

        self.task_list_interface.new_project_signal.connect(self.start_import)
        self.task_list_interface.project_selected.connect(self.enter_labeling_mode)
        self.label_interface.request_ai_signal.connect(self.run_ai)
        # 标注页切换/新增 AI 模型后，立刻刷新 ai_worker 配置
        self.label_interface.ai_model_changed_signal.connect(self.on_ai_model_changed)
        self.label_interface.back_clicked.connect(self.return_to_tasks)
        
        self.worker = None      
        self.current_project = None
        self.click_pos = None   
        self.ai_worker = AiWorker()
        self.ai_worker.finished_signal.connect(self.on_ai_finished)
        self.ai_worker.error_signal.connect(self.on_ai_error)

        self.stack.setCurrentIndex(1)
        self.task_list_interface.refresh_data()

    def center_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def toggle_maximize(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()

    def switch_page(self, page_name):
        if page_name == "tasks": self.return_to_tasks()

    def return_to_tasks(self):
        self.stack.setCurrentIndex(1)
        self.task_list_interface.refresh_data()

    def pressWindow(self, event):
        if event.button() == Qt.LeftButton: self.click_pos = event.globalPos()

    def moveWindow(self, event):
        if self.click_pos and not self.isMaximized():
            move_point = event.globalPos() - self.click_pos
            self.move(self.pos() + move_point)
            self.click_pos = event.globalPos()

    def start_import(self, config_data):
        path = config_data['folder']
        project, videos, img_count = DataManager.import_folder(path, model_path=config_data['model'], class_list_str=config_data['classes'])
        if img_count == 0 and len(videos) == 0:
             QMessageBox.warning(self, "警告", "目录中未找到支持的图片或视频文件！")
             project.delete_instance(); return
        if config_data.get('name'):
            project.name = config_data['name']; project.save()
        self.current_project = project
        if videos: self.process_videos(videos)
        else: self.on_import_finished()

    def process_videos(self, videos):
        video_path = videos[0]
        self.progress_dialog = QProgressDialog("正在抽帧...", "取消", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()
        output_dir = os.path.join(DATA_DIR, "frames")
        self.worker = VideoExtractWorker(video_path, output_dir, fps=1)
        self.worker.progress_signal.connect(self.progress_dialog.setValue)
        self.worker.progress_signal.connect(self.progress_dialog.setLabelText)
        self.worker.finished_signal.connect(lambda dir: self.on_video_finished(dir, video_path))
        self.worker.start()

    def on_video_finished(self, frame_dir, video_path):
        self.progress_dialog.close()
        count = DataManager.add_frames(self.current_project.id, frame_dir, video_path)
        QMessageBox.information(self, "完成", f"视频处理完成，生成 {count} 张图片")
        self.on_import_finished()

    def on_import_finished(self):
        self.task_list_interface.refresh_data()
        QMessageBox.information(self, "成功", "任务创建成功！")

    def enter_labeling_mode(self, project_obj):
        self.current_project = project_obj
        items = MediaItem.select().where(MediaItem.project == self.current_project).order_by(MediaItem.file_path)
        all_files = [item.file_path for item in items]
        if not all_files:
            QMessageBox.information(self, "提示", "没有图片")
            return
        self.ai_worker.update_config(project_obj.model_path, project_obj.classes)
        self.stack.setCurrentIndex(2)
        
        # === 关键：传递 Project 对象，确保能加载和保存历史标签 ===
        self.label_interface.set_project(project_obj)
        
        target_path = all_files[0]
        for item in items:
            if not item.is_labeled: target_path = item.file_path; break
        self.label_interface.load_file_list(all_files, target_path)
        self.label_interface.load_image(target_path)

    def run_ai(self, image_path):
        if not self.ai_worker.isRunning():
            self.ai_worker.set_image(image_path); self.ai_worker.start()

    def on_ai_model_changed(self, model_path: str):
        """用户在标注页选择/切换 AI 模型后，立即更新推理线程配置。"""
        try:
            classes_str = self.current_project.classes if self.current_project else None
        except Exception:
            classes_str = None

        # 立刻更新 worker；如果模型路径无效，实际加载时会在 on_ai_error 里提示
        self.ai_worker.update_config(model_path, classes_str)
    
    def on_ai_finished(self, image_path, results):
        self.label_interface.apply_ai_results(results)

    def on_ai_error(self, err_msg):
        QMessageBox.critical(self, "AI 错误", f"识别失败: {err_msg}")