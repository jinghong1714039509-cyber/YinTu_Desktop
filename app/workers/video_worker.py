import cv2
import os
from PySide6.QtCore import QThread, Signal
from app.common.logger import logger

class VideoExtractWorker(QThread):
    progress_signal = Signal(int, str)  # 进度(0-100), 当前状态信息
    finished_signal = Signal(int)       # 完成信号，返回生成的图片数量

    def __init__(self, video_path, output_dir, fps=2):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.fps = fps
        self.is_running = True

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.progress_signal.emit(0, "无法打开视频文件")
            return

        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算跳帧间隔：例如原视频30帧，目标2帧，则每15帧取1个
        step = int(original_fps / self.fps) if self.fps > 0 else 30
        
        count = 0
        saved_count = 0
        
        os.makedirs(self.output_dir, exist_ok=True)

        while self.is_running:
            ret, frame = cap.read()
            if not ret:
                break
            
            if count % step == 0:
                frame_name = f"frame_{saved_count:06d}.jpg"
                save_path = os.path.join(self.output_dir, frame_name)
                cv2.imwrite(save_path, frame)
                saved_count += 1
                
                # 发送进度
                progress = int((count / total_frames) * 100)
                self.progress_signal.emit(progress, f"正在导出: {frame_name}")

            count += 1

        cap.release()
        self.finished_signal.emit(saved_count)
        logger.info(f"视频处理完成，共抽取 {saved_count} 帧")

    def stop(self):
        self.is_running = False