import os
from PySide6.QtWidgets import QMainWindow, QProgressDialog, QMessageBox
from PySide6.QtCore import Qt

from app.ui.views.home_interface import HomeInterface
from app.ui.views.label_interface import LabelInterface 
from app.services.data_manager import DataManager
from app.workers.video_worker import VideoExtractWorker
from app.common.config import DATA_DIR
from app.models.schema import MediaItem # <--- 新增导入

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YinTu Desktop - 开发版")
        self.resize(1000, 700)

        # 页面初始化
        self.home_interface = HomeInterface(self)
        self.label_interface = LabelInterface(self)

        # 信号连接
        self.home_interface.project_selected.connect(self.start_import)

        # 默认显示首页
        self.setCentralWidget(self.home_interface)
        
        # 成员变量
        self.worker = None
        self.current_project = None

    def start_import(self, path):
        print(f"开始导入: {path}")
        
        # 1. 数据库扫描
        project, videos, img_count = DataManager.import_folder(path)
        self.current_project = project
        
        print(f"扫描完成：发现 {img_count} 张图片, {len(videos)} 个视频")

        # 2. 如果有视频，开始抽帧
        if videos:
            self.process_videos(videos)
        else:
            self.on_import_finished()

    def process_videos(self, videos):
        # 简单起见，这里只处理第一个视频
        video_path = videos[0]
        
        # 进度条
        self.progress_dialog = QProgressDialog("正在抽帧...", "取消", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.show()

        # 启动线程
        output_dir = os.path.join(DATA_DIR, "frames")
        self.worker = VideoExtractWorker(video_path, output_dir, fps=1)
        self.worker.progress_signal.connect(self.progress_dialog.setValue)
        self.worker.progress_signal.connect(self.progress_dialog.setLabelText)
        self.worker.finished_signal.connect(lambda dir: self.on_video_finished(dir, video_path))
        self.worker.start()

    def on_video_finished(self, frame_dir, video_path):
        self.progress_dialog.close()
        # 把生成的帧入库
        count = DataManager.add_frames(self.current_project.id, frame_dir, video_path)
        QMessageBox.information(self, "完成", f"视频处理完成，生成 {count} 张图片")
        self.on_import_finished()

    def on_import_finished(self):
        """数据准备完毕，跳转到标注界面"""
        self.setWindowTitle(f"YinTu - {self.current_project.name}")
        
        # 1. 查询项目中的第一张图片
        first_item = MediaItem.select().where(
            MediaItem.project == self.current_project
        ).first()

        # 2. 切换界面
        self.setCentralWidget(self.label_interface)
        
        # 3. 加载图片
        if first_item:
            print(f"正在加载第一张图片: {first_item.file_path}")
            self.label_interface.load_image(first_item.file_path)
        else:
            QMessageBox.warning(self, "提示", "该文件夹下没有找到可显示的图片或视频帧")