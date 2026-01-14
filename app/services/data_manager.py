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
    def import_folder(path_str, model_path=None, class_list_str=None):
        # 1. 判断用户选择的是目录还是文件（视频）
        if os.path.isfile(path_str):
            folder_name = os.path.splitext(os.path.basename(path_str))[0]
            folder_path = os.path.dirname(path_str)
        else:
            folder_name = os.path.basename(path_str)
            folder_path = path_str

        # 2. 创建项目
        project, created = Project.get_or_create(
            path=path_str, # 存储用户选择的原始路径（可能是文件也可能是目录）
            defaults={
                'name': folder_name,
                'model_path': model_path,
                'classes': class_list_str
            }
        )
        if not created:
            project.model_path = model_path
            project.classes = class_list_str
            project.save()

        # 3. 扫描文件
        img_files = []
        video_files = []
        if os.path.isdir(folder_path):
            for root, dirs, files in os.walk(folder_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    full_path = os.path.join(root, f)
                    if ext in SUPPORTED_IMAGE_EXT:
                        img_files.append(full_path)
                    elif ext in SUPPORTED_VIDEO_EXT:
                        video_files.append(full_path)
        else:
            # 单文件（视频）
            ext = os.path.splitext(path_str)[1].lower()
            if ext in SUPPORTED_VIDEO_EXT:
                video_files.append(path_str)

        # 4. 写入 MediaItem
        if img_files:
            with db.atomic():
                for fp in img_files:
                    MediaItem.get_or_create(project=project, file_path=fp, defaults={'media_type': 'image'})
        return project, video_files, len(img_files)

    @staticmethod
    def add_frames(project_id, frame_dir, video_path):
        project = Project.get_by_id(project_id)
        data = []
        for f in sorted(os.listdir(frame_dir)):
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_IMAGE_EXT:
                fp = os.path.join(frame_dir, f)
                data.append({
                    'project': project,
                    'file_path': fp,
                    'media_type': 'image'
                })
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
            progress = int((labeled_count / total_count) * 100) if total_count else 0
            status = "标注中"
            if total_count == 0:
                status = "空项目"
            elif labeled_count == 0:
                status = "未标注"
            elif labeled_count == total_count:
                status = "已完成"

            status_color = "#007bff"
            if status == "已完成": status_color = "#28a745"
            elif status == "未标注": status_color = "#dc3545"
            elif status == "空项目": status_color = "#6c757d"

            stats_list.append({
                'name': p.name,
                'path': p.path,
                'total': total_count,
                'labeled': labeled_count,
                'progress': progress,
                'status': status,
                'status_color': status_color,
                'object': p
            })
        return stats_list

    @staticmethod
    def preview_delete_project(project_or_id):
        """删除前预览：统计将删除的数据库记录数量（不做实际删除）。

        返回示例：
        {
            "project_id": 1,
            "media_count": 120,
            "annotation_count": 560
        }
        """
        project_id = getattr(project_or_id, "id", project_or_id)

        media_q = MediaItem.select(MediaItem.id).where(MediaItem.project_id == project_id)
        media_ids = [m.id for m in media_q]
        media_count = len(media_ids)

        if media_ids:
            annotation_count = Annotation.select(Annotation.id).where(Annotation.media_item.in_(media_ids)).count()
        else:
            annotation_count = 0

        return {
            "project_id": project_id,
            "media_count": media_count,
            "annotation_count": annotation_count
        }

    @staticmethod
    def delete_project(project_or_id, delete_managed_files=False, delete_original_files=False):
        """删除任务（项目）及其关联数据。

        默认策略（推荐）：
        - delete_original_files=False：不删除用户原始图片/视频文件
        - delete_managed_files=False：不删除 DATA_DIR 下的托管文件（如抽帧产物）

        返回：
        {
            "ok": bool,
            "deleted": {"projects": int, "media": int, "annotations": int, "files": int},
            "error": str | None
        }
        """
        from app.common.config import DATA_DIR

        project_id = getattr(project_or_id, "id", project_or_id)
        result = {
            "ok": False,
            "deleted": {"projects": 0, "media": 0, "annotations": 0, "files": 0},
            "error": None
        }

        try:
            # 1) 预先收集 MediaItem（用于统计与可选的文件清理）
            media_list = list(MediaItem.select().where(MediaItem.project_id == project_id))
            media_ids = [m.id for m in media_list]

            managed_files_to_delete = []
            original_files_to_delete = []
            abs_data_dir = os.path.abspath(DATA_DIR)

            for m in media_list:
                p = (m.file_path or "").strip()
                if not p:
                    continue
                abs_p = os.path.abspath(p)

                # 托管文件：位于 DATA_DIR 下
                if abs_p.startswith(abs_data_dir):
                    if delete_managed_files and os.path.exists(abs_p):
                        managed_files_to_delete.append(abs_p)
                    continue

                # 原始文件：用户目录（高风险，默认不删）
                if delete_original_files and os.path.exists(abs_p):
                    original_files_to_delete.append(abs_p)

            # 2) 数据库删除（事务）：先删 Annotation，再删 MediaItem，再删 Project
            with db.atomic():
                if media_ids:
                    ann_deleted = Annotation.delete().where(Annotation.media_item.in_(media_ids)).execute()
                else:
                    ann_deleted = 0
                media_deleted = MediaItem.delete().where(MediaItem.project_id == project_id).execute()
                proj_deleted = Project.delete().where(Project.id == project_id).execute()

            result["deleted"]["annotations"] = int(ann_deleted)
            result["deleted"]["media"] = int(media_deleted)
            result["deleted"]["projects"] = int(proj_deleted)

            # 3) 文件删除（事务外执行）：失败不影响数据库一致性
            files_deleted = 0
            for fp in managed_files_to_delete:
                try:
                    if os.path.isdir(fp):
                        shutil.rmtree(fp, ignore_errors=True)
                    else:
                        os.remove(fp)
                    files_deleted += 1
                except Exception:
                    pass

            for fp in original_files_to_delete:
                try:
                    os.remove(fp)
                    files_deleted += 1
                except Exception:
                    pass

            result["deleted"]["files"] = files_deleted
            result["ok"] = True
            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    @staticmethod
    def save_annotations(image_path, box_data):
        media_item = MediaItem.get_or_none(MediaItem.file_path == image_path)
        if not media_item:
            return False

        # 清空旧标注
        Annotation.delete().where(Annotation.media_item == media_item).execute()

        # 写入新标注
        with db.atomic():
            for ann in box_data:
                # 兼容两种输入结构：
                # - 新结构：直接提供 x/y/w/h（归一化中心点+宽高）
                # - 旧结构：仅提供 rect=[x,y,w,h]
                x = ann.get('x', None)
                y = ann.get('y', None)
                w = ann.get('w', None)
                h = ann.get('h', None)

                if x is None or y is None or w is None or h is None:
                    rect = ann.get('rect', None)
                    if isinstance(rect, (list, tuple)) and len(rect) == 4:
                        x = rect[0] if x is None else x
                        y = rect[1] if y is None else y
                        w = rect[2] if w is None else w
                        h = rect[3] if h is None else h

                try:
                    x = float(x) if x is not None else 0.0
                    y = float(y) if y is not None else 0.0
                    w = float(w) if w is not None else 0.0
                    h = float(h) if h is not None else 0.0
                except Exception:
                    x, y, w, h = 0.0, 0.0, 0.0, 0.0

                Annotation.create(
                    media_item=media_item,
                    label=ann['label'],
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    shape_type=ann.get('shape_type', 'rect'),
                    points=ann.get('points', None),
                    confidence=ann.get('confidence', 1.0)
                )

        # 更新标注状态
        media_item.is_labeled = True if box_data else False
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

        # ============ 1. 获取类别映射 ============
        classes_list = []
        if project.classes:
            classes_list = [c.strip() for c in project.classes.split(',') if c.strip()]

        # 如果数据库中有 label 但 classes 为空，也补全一下
        db_labels = Annotation.select(Annotation.label).join(MediaItem).where(MediaItem.project == project).distinct()
        for l in db_labels:
            if l.label not in classes_list:
                classes_list.append(l.label)

        classes_list.sort()
        class_map = {name: i for i, name in enumerate(classes_list)}

        # classes.txt
        with open(os.path.join(output_dir, 'classes.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(classes_list))

        # ============ 2. COCO 初始化 ============
        coco_data = {
            "info": {
                "description": "YinTu Export",
                "date_created": str(datetime.datetime.now())
            },
            "images": [],
            "annotations": [],
            "categories": [{"id": i+1, "name": name} for i, name in enumerate(classes_list)]
        }
        coco_ann_id = 1

        # ============ 3. 遍历已标注图片 ============
        items = MediaItem.select().where(
            (MediaItem.project == project) &
            (MediaItem.is_labeled == True)
        )

        count = 0
        for item in items:
            annotations = list(item.annotations)
            if not annotations:
                continue

            file_basename = os.path.basename(item.file_path)
            name_no_ext = os.path.splitext(file_basename)[0]

            # 读取宽高
            reader = QImageReader(item.file_path)
            size = reader.size()
            width, height = size.width(), size.height()

            # ========== YOLO ==========
            if format_type == "YOLO":
                txt_path = os.path.join(output_dir, name_no_ext + ".txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    for ann in annotations:
                        cid = class_map.get(ann.label, -1)
                        if cid == -1:
                            continue
                        f.write(f"{cid} {ann.x:.6f} {ann.y:.6f} {ann.w:.6f} {ann.h:.6f}\n")

            # ========== VOC ==========
            elif format_type == "VOC":
                xml_path = os.path.join(output_dir, name_no_ext + ".xml")
                root = ET.Element("annotation")
                ET.SubElement(root, "filename").text = file_basename
                size_node = ET.SubElement(root, "size")
                ET.SubElement(size_node, "width").text = str(width)
                ET.SubElement(size_node, "height").text = str(height)
                ET.SubElement(size_node, "depth").text = "3"

                for ann in annotations:
                    obj = ET.SubElement(root, "object")
                    ET.SubElement(obj, "name").text = ann.label
                    bndbox = ET.SubElement(obj, "bndbox")

                    xmin = max(0, int((ann.x - ann.w/2) * width))
                    ymin = max(0, int((ann.y - ann.h/2) * height))
                    xmax = min(width, int((ann.x + ann.w/2) * width))
                    ymax = min(height, int((ann.y + ann.h/2) * height))

                    ET.SubElement(bndbox, "xmin").text = str(xmin)
                    ET.SubElement(bndbox, "ymin").text = str(ymin)
                    ET.SubElement(bndbox, "xmax").text = str(xmax)
                    ET.SubElement(bndbox, "ymax").text = str(ymax)

                xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(xmlstr)

            # ========== LabelMe ==========
            elif format_type == "LabelMe":
                json_path = os.path.join(output_dir, name_no_ext + ".json")
                labelme_data = {
                    "version": "5.0.1",
                    "flags": {},
                    "shapes": [],
                    "imagePath": file_basename,
                    "imageData": None,
                    "imageHeight": height,
                    "imageWidth": width
                }

                for ann in annotations:
                    shape = {
                        "label": ann.label,
                        "points": [],
                        "group_id": None,
                        "shape_type": "rectangle",
                        "flags": {}
                    }

                    xmin = (ann.x - ann.w/2) * width
                    ymin = (ann.y - ann.h/2) * height
                    xmax = (ann.x + ann.w/2) * width
                    ymax = (ann.y + ann.h/2) * height
                    shape["points"] = [[xmin, ymin], [xmax, ymax]]
                    labelme_data["shapes"].append(shape)

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(labelme_data, f, indent=2, ensure_ascii=False)

            # ========== COCO ==========
            elif format_type == "COCO":
                img_id = item.id
                coco_data["images"].append({
                    "id": img_id,
                    "width": width,
                    "height": height,
                    "file_name": file_basename
                })

                for ann in annotations:
                    cid = class_map.get(ann.label, -1)
                    if cid == -1:
                        continue

                    x_tl = (ann.x - ann.w/2) * width
                    y_tl = (ann.y - ann.h/2) * height
                    w_px = ann.w * width
                    h_px = ann.h * height

                    coco_data["annotations"].append({
                        "id": coco_ann_id,
                        "image_id": img_id,
                        "category_id": cid+1,
                        "segmentation": [],
                        "area": float(w_px * h_px),
                        "bbox": [float(x_tl), float(y_tl), float(w_px), float(h_px)],
                        "iscrowd": 0
                    })
                    coco_ann_id += 1

            count += 1

        if format_type == "COCO":
            json_path = os.path.join(output_dir, "result.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(coco_data, f, indent=2, ensure_ascii=False)

        return count
