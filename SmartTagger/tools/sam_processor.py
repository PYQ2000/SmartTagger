# -*- coding = utf-8 -*-
# @Time :2024/10/28 18:48
# @Author :Pang
# @File :  sam_processor.py
# @Description :

from ultralytics import SAM
from PIL import Image
import numpy as np
import os
from shapely.geometry import Polygon


class SAMProcessor:
    def __init__(self):
        pass

    @staticmethod
    def process(image_path, visible_labels, label_folder, label_type, reduction_factor=4, iou_threshold=0.6,
                model_path="weights/sam2_b.pt", conf=0.25):
        image = Image.open(image_path)
        width, height = image.size
        # print(f"Width: {width}, Height: {height}")

        if label_type == 'box':
            input_points = None
            input_boxes = SAMProcessor.convert_boxes(visible_labels, width, height)
        elif label_type == 'point':
            input_points = SAMProcessor.convert_points(visible_labels, width, height)
            input_boxes = None
        else:
            raise ValueError("Invalid label type. Must be 'box' or 'point'.")

        print(str(model_path))

        sam_model = SAM(str(model_path))
        sam_result = sam_model(source=image_path,
                               imgsz=1280,
                               conf=conf,
                               save=False,
                               save_txt=False,
                               bboxes=input_boxes,
                               points=input_points,
                               # line_width=3,
                               )

        # Extract the xyn array
        xyn_data = sam_result[0].masks.xyn

        polygon_folder = os.path.join(label_folder, 'Polygon')
        os.makedirs(polygon_folder, exist_ok=True)

        image_name = os.path.splitext(os.path.basename(image_path))[0]
        output_file = f"{image_name}.txt"
        output_path = os.path.join(polygon_folder, output_file)

        # Read existing labels (if the file exists)
        existing_labels = []
        if os.path.exists(output_path):
            with open(output_path, 'r') as file:
                existing_labels = [line.strip() for line in file.readlines()]

        # Process new labels
        new_labels = []
        for item, coordinates in zip(visible_labels, xyn_data):
            class_id = item['class_id']
            # Reduce the number of points
            reduced_coords = coordinates[::reduction_factor]
            coords_str = ' '.join(map(str, reduced_coords.flatten()))
            new_label = f"{class_id} {coords_str}"
            new_labels.append(new_label)

        # Check for duplicates and update or add new labels
        updated_labels = existing_labels.copy()
        for new_label in new_labels:
            is_duplicate = False
            for i, existing_label in enumerate(updated_labels):
                if calculate_iou(new_label, existing_label) > iou_threshold:
                    updated_labels[i] = new_label  # Replace duplicate label
                    is_duplicate = True
                    break
            if not is_duplicate:
                updated_labels.append(new_label)  # Add new label

        # Save updated labels
        with open(output_path, 'w') as file:
            for label in updated_labels:
                file.write(f"{label}\n")

        return {"status": "success", "message": "SAM segmentation completed and results saved"}

    @staticmethod
    def convert_boxes(visible_labels, width, height):
        converted_boxes = []
        for item in visible_labels:
            bbox = item['bbox']
            x_center = bbox[0] * width
            y_center = bbox[1] * height
            box_width = bbox[2] * width
            box_height = bbox[3] * height

            x_min = x_center - (box_width / 2)
            y_min = y_center - (box_height / 2)
            x_max = x_center + (box_width / 2)
            y_max = y_center + (box_height / 2)

            converted_boxes.append([x_min, y_min, x_max, y_max])
        return np.array(converted_boxes)

    @staticmethod
    def convert_points(visible_labels, width, height):
        converted_points = []
        for item in visible_labels:
            point = item['point']
            x = point[0] * width
            y = point[1] * height
            converted_points.append([x, y])
        return np.array(converted_points)

    def generate_mask(self, image, bbox):
        pass

    def interact(self, image, point):
        pass

def calculate_iou(label1, label2):
    # Extract coordinates from label strings
    coords1 = np.array([float(x) for x in label1.split()[1:]]).reshape(-1, 2)
    coords2 = np.array([float(x) for x in label2.split()[1:]]).reshape(-1, 2)

    # Create Shapely polygon objects
    poly1 = Polygon(coords1)
    poly2 = Polygon(coords2)

    # Calculate intersection and union
    intersection = poly1.intersection(poly2).area
    union = poly1.union(poly2).area

    # Calculate IOU
    iou = intersection / union if union > 0 else 0

    return iou