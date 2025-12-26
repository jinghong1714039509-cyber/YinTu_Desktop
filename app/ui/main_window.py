import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QStackedWidget, QMessageBox, QProgressDialog, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QGuiApplication

# 导入组件
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
        self.setWindowTitle("YinTu Desktop")
        self.resize(1280, 800)
        
        self.center_window()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 核心容器
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.central_widget.setStyleSheet("""
            #CentralWidget {
                background-color: #f4f6f9;
                border-radius: 12px; 
                border: 1px solid #dcdcdc;
            }
        """)
        self.setCentralWidget(self.central_widget)
        
        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.central_widget.setGraphicsEffect(shadow)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 左侧：侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        self.main_layout.addWidget(self.sidebar)

        # 右侧：内容区域
        self.content_container = QWidget()
        # 关键：给右侧容器也设置圆角，防止直角溢出
        self.content_container.setStyleSheet("""
            border-top-right-radius: 12px;
            border-bottom-right-radius: 12px;
            background-color: transparent;
        """) 
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # 顶部 Header
        self.header = Header()
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

        # --- 信号连接 ---
        self.task_list_interface.new_project_signal.connect(self.start_import)
        self.task_list_interface.project_selected.connect(self.enter_labeling_mode)
        self.label_interface.request_ai_signal.connect(self.run_ai)
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
        self.move((screen.width() - size.width()) // 2, 
                  (screen.height() - size.height()) // 2)

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def switch_page(self, page_name):
        if page_name == "tasks":
            self.return_to_tasks()

    def return_to_tasks(self):
        self.stack.setCurrentIndex(1)
        self.task_list_interface.refresh_data()

    def pressWindow(self, event):
        if event.button() == Qt.LeftButton:
            self.click_pos = event.globalPos()

    def moveWindow(self, event):
        if self.click_pos and not self.isMaximized():
            move_point = event.globalPos() - self.click_pos
            self.move(self.pos() + move_point)
            self.click_pos = event.globalPos()

    def start_import(self, config_data):
        path = config_data['folder']
        project, videos, img_count = DataManager.import_folder(
            path, 
            model_path=config_data['model'],
            class_list_str=config_data['classes']
        )
        
        # 这里的检查之前加过了，如果没有文件会直接弹窗警告并删除项目
        # import_folder 方法里已经处理了，这里我们只需要处理成功的情况
        if img_count == 0 and len(videos) == 0:
             # 如果是空项目，DataManager 其实创建了项目
             # 我们在这里做二次校验
             QMessageBox.warning(self, "警告", "目录中未找到支持的图片或视频文件！")
             project.delete_instance()
             return

        if config_data.get('name'):
            project.name = config_data['name']
            project.save()

        self.current_project = project

        if videos:
            self.process_videos(videos)
        else:
            self.on_import_finished()

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
        """进入标注模式（核心修改：先检查文件，没文件不跳转）"""
        print(f"进入项目: {project_obj.name}")
        self.current_project = project_obj
        
        # 查询文件
        items = MediaItem.select().where(
            MediaItem.project == self.current_project
        ).order_by(MediaItem.file_path)

        all_files = [item.file_path for item in items]
        
        # === 修改点：如果没有文件，弹出白底警告，并且不切换页面 ===
        if not all_files:
            self.show_white_msgbox("提示", "该任务下没有找到可显示的图片")
            # 保持在 Index 1 (任务列表)，不要切到 Index 2
            return

        # 如果有文件，才切换界面
        self.ai_worker.update_config(project_obj.model_path, project_obj.classes)
        self.stack.setCurrentIndex(2) # 切换到标注页
        self.label_interface.set_project(project_obj)
        
        target_path = all_files[0]
        for item in items:
            if not item.is_labeled:
                target_path = item.file_path
                break
        self.label_interface.load_file_list(all_files, target_path)
        self.label_interface.load_image(target_path)

    # 辅助方法：显示白色背景的提示框 (解决黑屏问题)
    def show_white_msgbox(self, title, content):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(content)
        msg.setStyleSheet("QMessageBox { background-color: white; color: #333; } QLabel { color: #333; }")
        msg.exec()

    def run_ai(self, image_path):
        if not self.ai_worker.isRunning():
            self.ai_worker.set_image(image_path)
            self.ai_worker.start()
    
    def on_ai_finished(self, image_path, results):
        self.label_interface.apply_ai_results(results)

    def on_ai_error(self, err_msg):
        self.label_interface.btnAI.setText("🤖")
        self.label_interface.btnAI.setEnabled(True)
        QMessageBox.critical(self, "AI 错误", f"识别失败: {err_msg}")