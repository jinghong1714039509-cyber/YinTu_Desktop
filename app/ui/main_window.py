import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QStackedWidget, QMessageBox, QProgressDialog)
from PySide6.QtCore import Qt

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
        self.setWindowFlags(Qt.FramelessWindowHint) 
        
        # 核心容器
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 左侧：侧边栏
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        self.main_layout.addWidget(self.sidebar)

        # 右侧：内容区域
        self.content_container = QWidget()
        self.content_container.setStyleSheet("background-color: #f4f6f9;") 
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # 顶部 Header
        self.header = Header()
        self.header.btn_close.clicked.connect(self.close) 
        self.header.mouseMoveEvent = self.moveWindow
        self.header.mousePressEvent = self.pressWindow
        self.content_layout.addWidget(self.header)

        # 页面堆栈
        self.stack = QStackedWidget()
        
        self.home_interface = HomeInterface()          # Index 0 (不使用了，但保留防止报错)
        self.task_list_interface = TaskListInterface() # Index 1
        self.label_interface = LabelInterface()        # Index 2
        
        self.stack.addWidget(self.home_interface)
        self.stack.addWidget(self.task_list_interface)
        self.stack.addWidget(self.label_interface)
        
        self.content_layout.addWidget(self.stack)
        self.main_layout.addWidget(self.content_container)

        # --- 信号连接 ---
        # 1. 任务列表的新建信号 -> 导入逻辑
        self.task_list_interface.new_project_signal.connect(self.start_import)
        
        # 2. 任务列表的点击信号 -> 进入标注
        self.task_list_interface.project_selected.connect(self.enter_labeling_mode)
        
        # 3. 标注界面的 AI 请求
        self.label_interface.request_ai_signal.connect(self.run_ai)
        
        # --- 业务变量 ---
        self.worker = None      
        self.current_project = None
        self.click_pos = None   

        self.ai_worker = AiWorker()
        self.ai_worker.finished_signal.connect(self.on_ai_finished)
        self.ai_worker.error_signal.connect(self.on_ai_error)

        # === 关键修改：默认显示任务列表 (Index 1) ===
        self.stack.setCurrentIndex(1)
        self.task_list_interface.refresh_data()

    def switch_page(self, page_name):
        # 侧边栏只有任务列表了，但为了兼容性保留判断
        if page_name == "tasks":
            self.task_list_interface.refresh_data()
            self.stack.setCurrentIndex(1)
        elif page_name == "label":
            # 如果需要回退到标注页（预留）
            pass

    def pressWindow(self, event):
        if event.button() == Qt.LeftButton:
            self.click_pos = event.globalPos()

    def moveWindow(self, event):
        if self.click_pos:
            move_point = event.globalPos() - self.click_pos
            self.move(self.pos() + move_point)
            self.click_pos = event.globalPos()

    # --- 导入逻辑 ---
    def start_import(self, config_data):
        path = config_data['folder']
        print(f"开始导入: {path}")
        
        project, videos, img_count = DataManager.import_folder(
            path, 
            model_path=config_data['model'],
            class_list_str=config_data['classes']
        )
        # 如果有自定义名称，更新一下
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
        # 刷新列表
        self.task_list_interface.refresh_data()
        QMessageBox.information(self, "成功", "任务创建成功！")

    # --- 进入标注模式 ---
    def enter_labeling_mode(self, project_obj):
        print(f"进入项目: {project_obj.name}")
        self.current_project = project_obj
        
        self.ai_worker.update_config(project_obj.model_path, project_obj.classes)

        self.stack.setCurrentIndex(2)
        self.label_interface.set_project(project_obj)

        items = MediaItem.select().where(
            MediaItem.project == self.current_project
        ).order_by(MediaItem.file_path)

        all_files = [item.file_path for item in items]
        
        if all_files:
            target_path = all_files[0]
            for item in items:
                if not item.is_labeled:
                    target_path = item.file_path
                    break
            self.label_interface.load_file_list(all_files, target_path)
            self.label_interface.load_image(target_path)
        else:
            QMessageBox.warning(self, "提示", "该任务下没有找到可显示的图片")

    # --- AI 逻辑 ---
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