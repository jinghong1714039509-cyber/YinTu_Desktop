import cv2
import os
from PySide6.QtCore import QThread, Signal

class VideoExtractWorker(QThread):
    # 信号：进度(0-100), 状态文字
    progress_signal = Signal(int, str)
    # 信号：完成，返回生成的图片文件夹路径
    finished_signal = Signal(str)

    def __init__(self, video_path, output_dir, fps=1):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.fps = fps # 每秒抽几帧
        self.is_running = True

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.progress_signal.emit(0, "无法打开视频")
            return

        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算跳帧步长
        step = int(original_fps / self.fps) if self.fps > 0 else 30
        
        # 创建输出目录
        video_name = os.path.splitext(os.path.basename(self.video_path))[0]
        save_dir = os.path.join(self.output_dir, video_name)
        os.makedirs(save_dir, exist_ok=True)

        count = 0
        saved_count = 0

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            if count % step == 0:
                frame_name = f"{video_name}_{saved_count:06d}.jpg"
                cv2.imwrite(os.path.join(save_dir, frame_name), frame)
                saved_count += 1
                
                # 发送进度
                progress = int((count / total_frames) * 100)
                self.progress_signal.emit(progress, f"正在处理: {video_name}")

            count += 1

        cap.release()
        self.finished_signal.emit(save_dir)

    def stop(self):
        self.is_running = False