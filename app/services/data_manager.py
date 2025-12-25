import os
import json
import shutil
import datetime
from xml.dom import minidom
import xml.etree.ElementTree as ET
from peewee import fn
from PySide6.QtGui import QImageReader
from app.models.schema import Project, MediaItem, Annotation, db
from app.common.config import SUPPORTED_IMAGE_EXT, SUPPORTED_VIDEO_EXT

class DataManager:
    # ... (前面的 import_folder, add_frames, get_all_projects_stats, save_annotations 保持不变) ...
    # ... 请直接保留原有的这几个方法，为了篇幅我这里省略重复代码 ...
    
    @staticmethod
    def import_folder(folder_path, model_path=None, class_list_str=None):
        folder_name = os.path.basename(folder_path)
        project, created = Project.get_or_create(
            path=folder_path,
            defaults={'name': folder_name, 'model_path': model_path, 'classes': class_list_str}
        )
        if not created:
            project.model_path = model_path
            project.classes = class_list_str
            project.save()
        
        image_files = []
        video_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(root, file)
                if ext in SUPPORTED_IMAGE_EXT:
                    image_files.append(full_path)
                elif ext in SUPPORTED_VIDEO_EXT:
                    video_files.append(full_path)
        
        existing_paths = {item.file_path for item in MediaItem.select(MediaItem.file_path).where(MediaItem.project == project)}
        new_items = []
        for img_path in image_files:
            if img_path not in existing_paths:
                new_items.append({'project': project, 'file_path': img_path, 'media_type': 'image'})
        
        if new_items:
            with db.atomic():
                for i in range(0, len(new_items), 100):
                    MediaItem.insert_many(new_items[i:i+100]).execute()
                    
        return project, video_files, len(image_files)

    @staticmethod
    def add_frames(project_id, frame_dir, video_path):
        frames = []
        for root, _, files in os.walk(frame_dir):
            for file in files:
                if file.lower().endswith('.jpg'):
                    frames.append(os.path.join(root, file))
        frames.sort()
        data = [{'project_id': project_id, 'file_path': p, 'media_type': 'frame'} for p in frames]
        if data:
            with db.atomic():
                for i in range(0, len(data), 100):
                    MediaItem.insert_many(data[i:i+100]).execute()
        return len(data)

    @staticmethod
    def get_all_projects_stats():
        stats_list = []
        projects = Project.select().order_by(Project.created_at.desc())
        for p in projects:
            total_count = MediaItem.select().where(MediaItem.project == p).count()
            labeled_count = MediaItem.select().where((MediaItem.project == p) & (MediaItem.is_labeled == True)).count()
            
            if total_count == 0: status, color = "空项目", "#6c757d"
            elif labeled_count == 0: status, color = "未标注", "#dc3545"
            elif labeled_count < total_count: status, color = "标注中", "#ffc107"
            else: status, color = "已完成", "#28a745"

            stats_list.append({
                'id': p.id, 'object': p, 'name': p.name, 'path': p.path,
                'total': total_count, 'labeled': labeled_count,
                'progress': int((labeled_count / total_count) * 100) if total_count > 0 else 0,
                'status': status, 'status_color': color
            })
        return stats_list

    @staticmethod
    def save_annotations(file_path, annotations_data):
        media_item = MediaItem.get_or_none(MediaItem.file_path == file_path)
        if not media_item: return False

        with db.atomic():
            Annotation.delete().where(Annotation.media_item == media_item).execute()
            if annotations_data:
                rows = []
                for ann in annotations_data:
                    rows.append({
                        'media_item': media_item,
                        'label': ann['label'],
                        'x': ann['rect'][0], 'y': ann['rect'][1], 'w': ann['rect'][2], 'h': ann['rect'][3],
                        'shape_type': ann.get('shape_type', 'rect'),
                        'points': ann.get('points', None)
                    })
                Annotation.insert_many(rows).execute()
                media_item.is_labeled = True
            else:
                media_item.is_labeled = False
            media_item.save()
        return True

    # === 全能导出功能实现 ===
    @staticmethod
    def export_dataset(project, output_dir, format_type):
        """
        导出数据集
        format_type: 'YOLO' | 'VOC' | 'COCO' | 'LabelMe'
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 1. 准备类别映射
        classes_list = []
        if project.classes:
            classes_list = [c.strip() for c in project.classes.split(',') if c.strip()]
        
        # 动态扫描所有类别以防遗漏
        db_labels = Annotation.select(Annotation.label).join(MediaItem).where(MediaItem.project == project).distinct()
        for l in db_labels:
            if l.label not in classes_list:
                classes_list.append(l.label)
        classes_list.sort()
        class_map = {name: i for i, name in enumerate(classes_list)}

        # 2. 导出 classes.txt (通用)
        with open(os.path.join(output_dir, 'classes.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(classes_list))

        # 3. 获取所有已标注图片
        items = MediaItem.select().where(
            (MediaItem.project == project) & (MediaItem.is_labeled == True)
        )

        # --- 初始化 COCO 数据结构 ---
        coco_data = {
            "info": {"description": "YinTu Export", "date_created": str(datetime.datetime.now())},
            "images": [],
            "annotations": [],
            "categories": [{"id": i+1, "name": name} for i, name in enumerate(classes_list)] # COCO id 从 1 开始
        }
        coco_ann_id = 1

        count = 0
        for item in items:
            annotations = list(item.annotations)
            if not annotations: continue

            file_basename = os.path.basename(item.file_path)
            name_no_ext = os.path.splitext(file_basename)[0]

            # 获取图片尺寸
            reader = QImageReader(item.file_path)
            size = reader.size()
            width, height = size.width(), size.height()
            if width <= 0 or height <= 0: continue # 跳过无效图片

            # === 格式 A: YOLO (.txt) ===
            if format_type == 'YOLO':
                txt_path = os.path.join(output_dir, name_no_ext + ".txt")
                with open(txt_path, 'w', encoding='utf-8') as f:
                    for ann in annotations:
                        cid = class_map.get(ann.label, -1)
                        if cid != -1:
                            # 数据库已经是归一化 cx, cy, w, h
                            f.write(f"{cid} {ann.x:.6f} {ann.y:.6f} {ann.w:.6f} {ann.h:.6f}\n")

            # === 格式 B: Pascal VOC (.xml) ===
            elif format_type == 'VOC':
                xml_path = os.path.join(output_dir, name_no_ext + ".xml")
                root = ET.Element('annotation')
                ET.SubElement(root, 'filename').text = file_basename
                size_node = ET.SubElement(root, 'size')
                ET.SubElement(size_node, 'width').text = str(width)
                ET.SubElement(size_node, 'height').text = str(height)
                ET.SubElement(size_node, 'depth').text = '3'

                for ann in annotations:
                    obj = ET.SubElement(root, 'object')
                    ET.SubElement(obj, 'name').text = ann.label
                    bndbox = ET.SubElement(obj, 'bndbox')
                    
                    # 归一化 -> 像素坐标
                    xmin = max(0, int((ann.x - ann.w/2) * width))
                    ymin = max(0, int((ann.y - ann.h/2) * height))
                    xmax = min(width, int((ann.x + ann.w/2) * width))
                    ymax = min(height, int((ann.y + ann.h/2) * height))

                    ET.SubElement(bndbox, 'xmin').text = str(xmin)
                    ET.SubElement(bndbox, 'ymin').text = str(ymin)
                    ET.SubElement(bndbox, 'xmax').text = str(xmax)
                    ET.SubElement(bndbox, 'ymax').text = str(ymax)
                
                xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
                with open(xml_path, 'w', encoding='utf-8') as f:
                    f.write(xmlstr)

            # === 格式 C: LabelMe (.json) ===
            elif format_type == 'LabelMe':
                labelme_data = {
                    "version": "5.0.1",
                    "flags": {},
                    "shapes": [],
                    "imagePath": file_basename,
                    "imageData": None, # 不嵌入图片数据以减小体积
                    "imageHeight": height,
                    "imageWidth": width
                }

                for ann in annotations:
                    shape = {
                        "label": ann.label,
                        "group_id": None,
                        "description": "",
                        "flags": {}
                    }
                    
                    if ann.shape_type == 'polygon' and ann.points:
                        shape['shape_type'] = 'polygon'
                        # 数据库存的是归一化 [[0.1, 0.2], ...] -> 转像素 [[100, 200], ...]
                        norm_pts = json.loads(ann.points)
                        shape['points'] = [[p[0]*width, p[1]*height] for p in norm_pts]
                    else:
                        shape['shape_type'] = 'rectangle'
                        xmin = (ann.x - ann.w/2) * width
                        ymin = (ann.y - ann.h/2) * height
                        xmax = (ann.x + ann.w/2) * width
                        ymax = (ann.y + ann.h/2) * height
                        shape['points'] = [[xmin, ymin], [xmax, ymax]]
                    
                    labelme_data['shapes'].append(shape)
                
                json_path = os.path.join(output_dir, name_no_ext + ".json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(labelme_data, f, indent=2, ensure_ascii=False)

            # === 格式 D: COCO (准备数据) ===
            elif format_type == 'COCO':
                # 添加图片信息
                img_id = item.id # 使用数据库 ID 作为唯一标识
                coco_data['images'].append({
                    "id": img_id,
                    "width": width,
                    "height": height,
                    "file_name": file_basename
                })

                for ann in annotations:
                    cid = class_map.get(ann.label, -1)
                    if cid == -1: continue
                    
                    # COCO bbox: [x_topleft, y_topleft, w, h] (像素)
                    x_tl = (ann.x - ann.w/2) * width
                    y_tl = (ann.y - ann.h/2) * height
                    w_px = ann.w * width
                    h_px = ann.h * height
                    
                    segmentation = []
                    # 如果有分割信息
                    if ann.shape_type == 'polygon' and ann.points:
                        norm_pts = json.loads(ann.points) # [[x,y], [x,y]]
                        # COCO segmentation 是一维列表 [x1, y1, x2, y2, ...]
                        poly_px = []
                        for p in norm_pts:
                            poly_px.append(p[0] * width)
                            poly_px.append(p[1] * height)
                        segmentation.append(poly_px)
                    
                    coco_data['annotations'].append({
                        "id": coco_ann_id,
                        "image_id": img_id,
                        "category_id": cid + 1, # COCO id 从 1 开始
                        "segmentation": segmentation,
                        "area": w_px * h_px, # 粗略计算
                        "bbox": [x_tl, y_tl, w_px, h_px],
                        "iscrowd": 0
                    })
                    coco_ann_id += 1

            count += 1

        # === 保存 COCO 大文件 ===
        if format_type == 'COCO':
            json_path = os.path.join(output_dir, "result.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(coco_data, f, indent=2, ensure_ascii=False)
            
        return count