import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QStackedWidget, QMessageBox, QProgressDialog)
from PySide6.QtCore import Qt

# 导入组件
from app.ui.components.sidebar import Sidebar
from app.ui.components.header import Header
from app.ui.views.home_interface import HomeInterface
from app.ui.views.label_interface import LabelInterface
from app.ui.views.task_list_interface import TaskListInterface # 新增导入
from app.services.data_manager import DataManager
from app.workers.video_worker import VideoExtractWorker
from app.workers.ai_worker import AiWorker # 新增导入
from app.common.config import DATA_DIR
from app.models.schema import MediaItem

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YinTu Desktop")
        self.resize(1280, 800)
        
        # --- 1. 设置无边框窗口 (网页感) ---
        self.setWindowFlags(Qt.FramelessWindowHint) 
        
        # 核心容器
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- 2. 左侧：侧边栏 ---
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.switch_page)
        self.main_layout.addWidget(self.sidebar)

        # --- 3. 右侧：内容区域容器 ---
        self.content_container = QWidget()
        self.content_container.setStyleSheet("background-color: #f4f6f9;") # AdminLTE 浅灰底色
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # 3.1 顶部 Header
        self.header = Header()
        self.header.btn_close.clicked.connect(self.close) # 连接关闭按钮
        # 允许拖拽 Header 移动窗口
        self.header.mouseMoveEvent = self.moveWindow
        self.header.mousePressEvent = self.pressWindow
        self.content_layout.addWidget(self.header)

        # 3.2 页面堆栈 (Home / TaskList / Label)
        self.stack = QStackedWidget()
        
        self.home_interface = HomeInterface()          # Index 0: 统计/首页
        self.task_list_interface = TaskListInterface() # Index 1: 任务列表
        self.label_interface = LabelInterface()        # Index 2: 标注工作台
        
        self.stack.addWidget(self.home_interface)
        self.stack.addWidget(self.task_list_interface)
        self.stack.addWidget(self.label_interface)
        
        self.content_layout.addWidget(self.stack)

        # 将右侧容器加入主布局
        self.main_layout.addWidget(self.content_container)

        # --- 信号连接 ---
        # 1. 首页导入
        self.home_interface.project_selected.connect(self.start_import)
        
        # 2. 任务列表点击进入
        self.task_list_interface.project_selected.connect(self.enter_labeling_mode)
        
        # 3. 标注界面请求 AI
        self.label_interface.request_ai_signal.connect(self.run_ai)
        
        # --- 业务变量初始化 ---
        self.worker = None      # 视频抽帧线程
        self.ai_worker = None   # AI 推理线程
        self.current_project = None
        self.click_pos = None   # 窗口拖拽坐标缓存

        # 初始化 AI 线程
        self.ai_worker = AiWorker()
        self.ai_worker.finished_signal.connect(self.on_ai_finished)
        self.ai_worker.error_signal.connect(self.on_ai_error)

    def switch_page(self, page_name):
        """侧边栏切换逻辑"""
        if page_name == "stats":
            self.stack.setCurrentIndex(0) # HomeInterface
        elif page_name == "tasks":
            # 切换到列表时，自动刷新数据
            self.task_list_interface.refresh_data()
            self.stack.setCurrentIndex(1) # TaskListInterface
        elif page_name == "label":
            # 点击“标注任务”时，默认跳转到任务列表让用户选，而不是直接进空的工作台
            self.sidebar.btn_tasks.click()
        elif page_name == "settings":
            QMessageBox.information(self, "提示", "设置功能开发中...")

    # --- 窗口拖拽逻辑 ---
    def pressWindow(self, event):
        if event.button() == Qt.LeftButton:
            self.click_pos = event.globalPos()

    def moveWindow(self, event):
        if self.click_pos:
            move_point = event.globalPos() - self.click_pos
            self.move(self.pos() + move_point)
            self.click_pos = event.globalPos()

    # --- 业务流程：导入数据 ---
    def start_import(self, path):
        print(f"开始导入: {path}")
        project, videos, img_count = DataManager.import_folder(path)
        self.current_project = project
        print(f"扫描完成：发现 {img_count} 张图片, {len(videos)} 个视频")

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
        """导入完成后，自动跳转到任务列表"""
        QMessageBox.information(self, "成功", "项目导入成功！请在任务列表中查看。")
        self.sidebar.btn_tasks.click() # 模拟点击切换到任务列表

    # --- 业务流程：进入标注模式 ---
    def enter_labeling_mode(self, project_obj):
        """从卡片点击进入标注界面"""
        print(f"进入项目: {project_obj.name}")
        self.current_project = project_obj
        
        # 1. 切换到标注页 (Index 2)
        self.stack.setCurrentIndex(2)
        
        # 2. 加载该项目的第一张图片
        first_item = MediaItem.select().where(
            MediaItem.project == self.current_project
        ).first()

        if first_item:
            self.label_interface.load_image(first_item.file_path)
        else:
            QMessageBox.warning(self, "提示", "该项目下没有找到可显示的图片")

    # --- 业务流程：AI 自动标注 ---
    def run_ai(self, image_path):
        """启动 AI 线程"""
        if not self.ai_worker.isRunning():
            self.ai_worker.set_image(image_path)
            self.ai_worker.start()
    
    def on_ai_finished(self, image_path, results):
        """AI 完成，通知界面画框"""
        self.label_interface.apply_ai_results(results)

    def on_ai_error(self, err_msg):
        self.label_interface.btnAI.setText("🤖 AI 自动识别")
        self.label_interface.btnAI.setEnabled(True)
        QMessageBox.critical(self, "AI 错误", f"识别失败: {err_msg}")