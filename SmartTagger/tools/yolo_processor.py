# -*- coding = utf-8 -*-
# @Time :2024/10/28 18:48
# @Author :Pang
# @File :  yolo_processor.py
# @Description :


# tools/yolo_processor.py

from ultralytics import YOLO
from PIL import Image

class YOLOProcessor:
    def __init__(self, weight_path, conf_threshold=0.25, iou_threshold=0.6):
        self.model = YOLO(weight_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def process_image(self, image_path):
        image = Image.open(image_path)
        results = self.model(image, conf=self.conf_threshold, iou=self.iou_threshold)[0]
        return results, image.size

    @staticmethod
    def convert_to_yolo_format(box, img_size):
        x1, y1, x2, y2, conf, class_id = box
        width = x2 - x1
        height = y2 - y1
        center_x = x1 + width / 2
        center_y = y1 + height / 2

        img_width, img_height = img_size
        center_x /= img_width
        center_y /= img_height
        width /= img_width
        height /= img_height

        return center_x, center_y, width, height, conf, int(class_id)

    @staticmethod
    def save_results(save_path, results, img_size):
        with open(save_path, 'w') as f:
            for box in results.boxes.data.tolist():
                center_x, center_y, width, height, _, class_id = YOLOProcessor.convert_to_yolo_format(box, img_size)
                f.write(f"{int(class_id)} {center_x} {center_y} {width} {height}\n")

    @staticmethod
    def calculate_iou(box1, box2):
        # Convert YOLO format to (x1, y1, x2, y2)
        def yolo_to_corners(box):
            center_x, center_y, width, height = box
            x1 = center_x - width / 2
            y1 = center_y - height / 2
            x2 = center_x + width / 2
            y2 = center_y + height / 2
            return [x1, y1, x2, y2]

        box1 = yolo_to_corners(box1)
        box2 = yolo_to_corners(box2)

        # Calculate intersection area
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        # Calculate union area
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        # Calculate IoU
        iou = intersection / union if union > 0 else 0
        return iou
