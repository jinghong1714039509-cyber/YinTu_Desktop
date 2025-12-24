from PySide6.QtCore import QThread, Signal
from ultralytics import YOLO
from app.common.logger import logger

class AutoLabelWorker(QThread):
    finished_signal = Signal(dict) # 返回 {path: [boxes...]}

    def __init__(self, model_path, image_paths):
        super().__init__()
        self.model_path = model_path
        self.image_paths = image_paths # 图片路径列表

    def run(self):
        logger.info(f"开始加载模型: {self.model_path}")
        try:
            model = YOLO(self.model_path)
            results = model(self.image_paths, verbose=False)
            
            output_data = {}
            
            for res in results:
                path = res.path
                boxes_list = []
                for box in res.boxes:
                    # 提取 xywhn (归一化坐标) 和 class
                    cls_id = int(box.cls[0])
                    label_name = model.names[cls_id]
                    xywh = box.xywhn[0].tolist() # x, y, w, h
                    conf = float(box.conf[0])
                    
                    boxes_list.append({
                        "label": label_name,
                        "rect": xywh,
                        "conf": conf
                    })
                output_data[path] = boxes_list
            
            self.finished_signal.emit(output_data)
            logger.info("AI 推理完成")
            
        except Exception as e:
            logger.error(f"AI 推理失败: {e}")