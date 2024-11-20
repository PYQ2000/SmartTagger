# -*- coding = utf-8 -*-
# @Time :2024/10/28 18:48
# @Author :Pang
# @File :  image_view.py
# @Description :


from PySide6.QtWidgets import (QLabel)
from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QBrush, QPolygonF, QFont, QCursor


class ImageView(QLabel):
    label_selected = Signal(int, str)  # Signal to emit when a label is selected
    label_added = Signal(str, list)  # Signal for when a label is added
    sam_segmentation_performed = Signal(str, list)  # Signal for when a SAM label is added


    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.pixmap = None
        self.scaled_pixmap = None
        self.box_labels = []
        self.polygon_labels = []
        self.point_labels = []
        self.visible_box_labels = set()
        self.visible_polygon_labels = set()
        self.visible_point_labels = set()
        self.class_colors = {}
        self.selected_box_label = None
        self.selected_polygon_label = None
        self.selected_point_label = None
        self.class_names = {}
        self.active_label_type = None  # Add tracking for the current active label type

        # New attributes for drawing
        self.drawing = False
        self.current_item = None
        self.start_point = None
        self.points = []
        self.is_sam = False

        self.setMouseTracking(True)
        self.drawing_complete = False

    def set_active_label_type(self, label_type):
        """Set the current active label type"""
        self.active_label_type = label_type
        self.update()

    def load_image(self, image_path):
        self.pixmap = QPixmap(image_path)
        self.update_scaled_pixmap()

    def update_scaled_pixmap(self):
        if self.pixmap:
            self.scaled_pixmap = self.pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.update()

    def set_labels(self, box_labels, polygon_labels, point_labels, class_colors, class_names):
        self.box_labels = box_labels
        self.polygon_labels = polygon_labels
        self.point_labels = point_labels
        self.class_colors = class_colors
        self.class_names = class_names

        self.visible_box_labels = set(range(len(self.box_labels)))
        self.visible_polygon_labels = set(range(len(self.polygon_labels)))
        self.visible_point_labels = set(range(len(self.point_labels)))

        self.update()

    def set_label_visibility(self, label_index, is_visible, label_type):
        if label_type == 'box':
            if is_visible:
                self.visible_box_labels.add(label_index)
            else:
                self.visible_box_labels.discard(label_index)
        elif label_type == 'polygon':
            if is_visible:
                self.visible_polygon_labels.add(label_index)
            else:
                self.visible_polygon_labels.discard(label_index)
        elif label_type == 'point':
            if is_visible:
                self.visible_point_labels.add(label_index)
            else:
                self.visible_point_labels.discard(label_index)
        self.update()

    def set_selected_label(self, label_index, label_type):
        if label_type == 'polygon' and self.selected_polygon_label != label_index:
            self.selected_polygon_label = label_index
            self.label_selected.emit(label_index, 'polygon')
            self.update()
        elif label_type == 'box' and self.selected_box_label != label_index:
            self.selected_box_label = label_index
            self.label_selected.emit(label_index, 'box')
            self.update()
        elif label_type == 'point' and self.selected_point_label != label_index:
            self.selected_point_label = label_index
            self.label_selected.emit(label_index, 'point')
            self.update()
        elif label_type is None:
            if self.selected_polygon_label is not None or self.selected_box_label is not None or self.selected_point_label is not None:
                self.selected_polygon_label = None
                self.selected_box_label = None
                self.selected_point_label = None
                self.label_selected.emit(-1, 'none')

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.scaled_pixmap:
            painter = QPainter(self)

            x = (self.width() - self.scaled_pixmap.width()) // 2
            y = (self.height() - self.scaled_pixmap.height()) // 2

            painter.drawPixmap(x, y, self.scaled_pixmap)

            if self.active_label_type in [None, 'box']:
                for i, label in enumerate(self.box_labels):
                    if i in self.visible_box_labels:
                        self.draw_box_label(painter, label, i, x, y)

            if self.active_label_type in [None, 'polygon']:
                for i, label in enumerate(self.polygon_labels):
                    if i in self.visible_polygon_labels:
                        self.draw_polygon_label(painter, label, i, x, y)

            if self.active_label_type in [None, 'point']:
                for i, label in enumerate(self.point_labels):
                    if i in self.visible_point_labels:
                        self.draw_point_label(painter, label, i, x, y)

            # Draw current item being drawn
            if self.drawing and self.points:
                if self.active_label_type == "Point":
                    self.draw_point(painter, self.points[0], x, y)
                elif self.active_label_type == "Box":
                    if len(self.points) == 1:
                        self.draw_point(painter, self.points[0], x, y)
                    if self.current_preview:
                        self.draw_box(painter, self.current_preview, x, y)
                elif self.active_label_type == "Polygon":
                    self.draw_polygon(painter, self.points, x, y)
                    if self.current_preview:
                        self.draw_polygon(painter, self.current_preview, x, y)

            # Draw guide lines
            if self.drawing:
                self.draw_guide_lines(painter)

            painter.end()

    def draw_point_label(self, painter, label, index, x_offset, y_offset):
        color = self.class_colors.get(label['class_id'], QColor(255, 0, 0))
        point = label.get('point')
        if not point:
            return

        scaled_point = self.scale_point(point, self.pixmap.size(), self.scaled_pixmap.size())
        x, y = scaled_point
        x += x_offset
        y += y_offset

        if index == self.selected_point_label:
            painter.setPen(QPen(color, 6, Qt.PenStyle.SolidLine))  # Thicker when selected
        else:
            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))  # Increase default thickness

        painter.drawPoint(x, y)

        # Draw a circle to increase visibility
        painter.drawEllipse(x - 3, y - 3, 6, 6)

        # Draw label text next to the point
        painter.setPen(QPen(color, 1))
        painter.setFont(QFont('Arial', 8))
        label_text = f"{self.class_names.get(label['class_id'], str(label['class_id']))} {index}"
        painter.drawText(x + 5, y + 5, label_text)

    def draw_box_label(self, painter, label, index, x_offset, y_offset):
        color = self.class_colors.get(label['class_id'], QColor(255, 0, 0))
        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))

        bbox = label['bbox']
        scaled_bbox = self.scale_bbox(bbox, self.pixmap.size(), self.scaled_pixmap.size())

        rect = QRectF(x_offset + scaled_bbox[0], y_offset + scaled_bbox[1],
                      scaled_bbox[2], scaled_bbox[3])

        painter.drawRect(rect)

        if index == self.selected_box_label:
            transparent_color = QColor(color)
            transparent_color.setAlpha(128)
            painter.fillRect(rect, QBrush(transparent_color))

    def draw_polygon_label(self, painter, label, index, x_offset, y_offset):
        color = self.class_colors.get(label['class_id'], QColor(255, 0, 0))
        painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))

        polygon = label.get('polygon')
        scaled_polygon = self.scale_polygon(polygon, self.pixmap.size(), self.scaled_pixmap.size())
        if not scaled_polygon:
            return

        qt_polygon = QPolygonF([QPointF(x_offset + p[0], y_offset + p[1]) for p in scaled_polygon])

        # Draw polygon outline
        painter.drawPolygon(qt_polygon)

        # Fill color only when the current polygon is selected
        if index == self.selected_polygon_label:
            transparent_color = QColor(color)
            transparent_color.setAlpha(128)
            painter.setBrush(QBrush(transparent_color))
            painter.drawPolygon(qt_polygon)

        # Important: Reset the brush to ensure the next polygon is not filled
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # print(f"Drawing polygon label {index}, selected: {index == self.selected_polygon_label}")

    def scale_bbox(self, bbox, original_size, new_size):
        x_center, y_center, width, height = bbox
        x_scale = new_size.width() / original_size.width()
        y_scale = new_size.height() / original_size.height()

        new_width = width * x_scale * original_size.width()
        new_height = height * y_scale * original_size.height()
        new_x = (x_center - width / 2) * x_scale * original_size.width()
        new_y = (y_center - height / 2) * y_scale * original_size.height()

        return [new_x, new_y, new_width, new_height]

    def scale_polygon(self, polygon, original_size, new_size):
        x_scale = new_size.width() / original_size.width()
        y_scale = new_size.height() / original_size.height()
        return [(x * x_scale * original_size.width(), y * y_scale * original_size.height()) for x, y in polygon]

    def scale_point(self, point, original_size, new_size):
        x, y = point
        x_scale = new_size.width() / original_size.width()
        y_scale = new_size.height() / original_size.height()
        return (x * x_scale * original_size.width(), y * y_scale * original_size.height())

    def mousePressEvent(self, event):
        if self.drawing:
            point = self.map_to_image(event.position())
            self.add_point(point)

            if self.active_label_type == "Point":
                self.finish_drawing()
            elif self.active_label_type == "Box":
                if len(self.points) == 1:
                    self.current_preview = [self.points[0], self.points[0]]  # Initialize with two identical points
                elif len(self.points) == 2:
                    self.finish_drawing()
            elif self.active_label_type == "Polygon" and len(self.points) > 2 and self.is_near_start_point(point):
                self.finish_drawing()

            self.update()
        else:
            # Selection logic
            # Call the parent class mousePressEvent if needed
            super().mousePressEvent(event)
            if not self.pixmap or not self.active_label_type:
                return

            x = event.position().x() - (self.width() - self.scaled_pixmap.width()) // 2
            y = event.position().y() - (self.height() - self.scaled_pixmap.height()) // 2

            selected = False
            if self.active_label_type in [None, 'box']:
                for i, label in enumerate(self.box_labels):
                    if i in self.visible_box_labels:
                        bbox = self.scale_bbox(label['bbox'], self.pixmap.size(), self.scaled_pixmap.size())
                        if (bbox[0] <= x <= bbox[0] + bbox[2] and bbox[1] <= y <= bbox[1] + bbox[3]):
                            self.set_selected_label(i, 'box')
                            selected = True
                            break

            if not selected and self.active_label_type in [None, 'polygon']:
                for i, label in enumerate(self.polygon_labels):
                    if i in self.visible_polygon_labels:
                        polygon = self.scale_polygon(label['polygon'], self.pixmap.size(), self.scaled_pixmap.size())
                        if self.point_inside_polygon(x, y, polygon):
                            self.set_selected_label(i, 'polygon')
                            selected = True
                            break

            if not selected and self.active_label_type in [None, 'point']:
                for i, label in enumerate(self.point_labels):
                    if i in self.visible_point_labels:
                        point = self.scale_point(label['point'], self.pixmap.size(), self.scaled_pixmap.size())
                        if self.point_near_point(x, y, point):
                            self.set_selected_label(i, 'point')
                            selected = True
                            break

            if not selected:
                self.set_selected_label(None, None)



    def point_inside_polygon(self, x, y, polygon):
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def point_near_point(self, x, y, point, threshold=5):
        return ((x - point[0]) ** 2 + (y - point[1]) ** 2) <= threshold ** 2

    def resizeEvent(self, event):
        self.update_scaled_pixmap()

    def sizeHint(self):
        if self.pixmap:
            return self.pixmap.size()
        return super().sizeHint()

    def is_label_visible(self, label_index, label_type):
        if label_type == 'box':
            return label_index in self.visible_box_labels
        elif label_type == 'polygon':
            return label_index in self.visible_polygon_labels
        elif label_type == 'point':
            return label_index in self.visible_point_labels
        return False

    # drawing

    def create_crosshair_cursor(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.red, 1))
        painter.drawLine(16, 0, 16, 32)
        painter.drawLine(0, 16, 32, 16)
        painter.end()
        return QCursor(pixmap, 16, 16)

    def start_drawing(self, label_type, is_sam):
        self.active_label_type = label_type
        self.is_sam = is_sam
        self.drawing = True
        self.drawing_complete = False
        self.points = []
        self.current_item = None
        self.current_preview = None
        self.setCursor(self.create_crosshair_cursor())
        self.update()

    def mouseMoveEvent(self, event):
        if self.drawing:
            current_point = self.map_to_image(event.position())
            if self.active_label_type == "Box" and self.points:
                if len(self.points) == 1:
                    self.current_preview = [self.points[0], current_point]
                else:
                    self.current_preview = self.points[:2]  # Ensure we only use the first two points
            elif self.active_label_type == "Polygon" and self.points:
                self.current_preview = self.points + [current_point]
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drawing and not self.drawing_complete:
            if self.active_label_type == "Box" and len(self.points) == 1:
                self.current_item = self.points + [self.map_to_image(event.position())]
            self.update()
        else:
            super().mouseReleaseEvent(event)

    def add_point(self, point):
        self.points.append(point)
        # print(f"Point added: {point}")
        if self.active_label_type == "Box" and len(self.points) > 2:
            self.points = self.points[:2]  # Keep only the first two points for Box
        self.current_preview = self.points.copy()

    def is_near_start_point(self, point, threshold=0.01):
        if len(self.points) > 2:
            start_point = self.points[0]
            return ((point[0] - start_point[0]) ** 2 + (point[1] - start_point[1]) ** 2) < threshold ** 2
        return False

    def finish_drawing(self):
        self.drawing = False
        self.setCursor(Qt.ArrowCursor)  # Reset the cursor
        if self.is_sam:
            self.perform_sam_segmentation()
        else:
            self.save_label()


    def save_label(self):
        self.label_added.emit(self.active_label_type, self.points)
        self.clear_drawing()

    def clear_drawing(self):
        self.drawing = False
        self.drawing_complete = False
        if hasattr(self, 'current_preview'):
            del self.current_preview
        self.current_item = None
        self.points = []
        self.update()

    def perform_sam_segmentation(self):
        self.sam_segmentation_performed.emit(self.active_label_type, self.points)
        self.clear_drawing()


    def map_to_image(self, point):
        x = (point.x() - (self.width() - self.scaled_pixmap.width()) // 2) / self.scaled_pixmap.width()
        y = (point.y() - (self.height() - self.scaled_pixmap.height()) // 2) / self.scaled_pixmap.height()
        return (x, y)

    def draw_point(self, painter, point, x_offset, y_offset):
        scaled_point = (point[0] * self.scaled_pixmap.width() + x_offset,
                        point[1] * self.scaled_pixmap.height() + y_offset)
        painter.setPen(QPen(Qt.red, 6))
        painter.drawPoint(QPointF(*scaled_point))

    def draw_box(self, painter, box, x_offset, y_offset):
        if not box or len(box) < 2:
            # If we don't have enough points, just draw what we have
            if box and len(box) == 1:
                self.draw_point(painter, box[0], x_offset, y_offset)
            return

        scaled_box = [
            (box[0][0] * self.scaled_pixmap.width() + x_offset,
             box[0][1] * self.scaled_pixmap.height() + y_offset),
            (box[1][0] * self.scaled_pixmap.width() + x_offset,
             box[1][1] * self.scaled_pixmap.height() + y_offset)
        ]
        painter.setPen(QPen(Qt.red, 2))
        painter.drawRect(QRectF(QPointF(*scaled_box[0]), QPointF(*scaled_box[1])))

    def draw_polygon(self, painter, polygon, x_offset, y_offset):
        if not polygon:
            return

        scaled_polygon = [
            (p[0] * self.scaled_pixmap.width() + x_offset,
             p[1] * self.scaled_pixmap.height() + y_offset)
            for p in polygon
        ]
        painter.setPen(QPen(Qt.red, 2))

        # Draw lines between points
        for i in range(len(scaled_polygon) - 1):
            painter.drawLine(QPointF(*scaled_polygon[i]), QPointF(*scaled_polygon[i + 1]))

        # Draw points
        for point in scaled_polygon:
            painter.drawEllipse(QPointF(*point), 3, 3)

        # Draw line from last point to first point if near
        if len(scaled_polygon) > 2 and self.is_near_start_point(polygon[-1]):
            painter.drawLine(QPointF(*scaled_polygon[-1]), QPointF(*scaled_polygon[0]))


    def draw_guide_lines(self, painter):
        if self.current_item:
            last_point = self.current_item[-1] if isinstance(self.current_item, list) else self.current_item[1]
            x = last_point[0] * self.scaled_pixmap.width() + (self.width() - self.scaled_pixmap.width()) // 2
            y = last_point[1] * self.scaled_pixmap.height() + (self.height() - self.scaled_pixmap.height()) // 2

            painter.setPen(QPen(Qt.gray, 1, Qt.DashLine))
            painter.drawLine(0, y, self.width(), y)
            painter.drawLine(x, 0, x, self.height())
