# -*- coding = utf-8 -*-
# @Time :2024/10/28 18:47
# @Author :Pang
# @File :  main_window.py
# @Description :


import random
import os
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton,
                               QWidget, QListWidget, QSplitter, QFileDialog, QLabel,
                               QListWidgetItem, QCheckBox, QTabWidget, QMessageBox,
                               QDialog, QButtonGroup, QRadioButton, QComboBox,
                               QLineEdit, QDialogButtonBox, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from ui.image_view import ImageView
from tools.sam_processor import SAMProcessor
from tools.yolo_processor import YOLOProcessor


class CustomListItem(QWidget):
    visibility_changed = Signal(int, bool, str)

    def __init__(self, text, index, label_type, parent=None):
        super().__init__(parent)
        self.index = index
        self.label_type = label_type
        self.is_visible = True
        self.label_visibility = {
            'box': set(),
            'polygon': set(),
            'point': set()
        }
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 2, 2)
        layout.setSpacing(7)

        self.class_colors = {}

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.clicked.connect(self.on_checkbox_clicked)
        layout.addWidget(self.checkbox)


        self.label = QLabel(text)
        layout.addWidget(self.label)
        layout.addStretch()


    def on_checkbox_clicked(self):
        self.is_visible = self.checkbox.isChecked()
        self.visibility_changed.emit(self.index, self.is_visible, self.label_type)

    def get_text(self):
        return self.label.text()

class ScrollableLabel(QScrollArea):
    def __init__(self, text):
        super().__init__()
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        content = QWidget()
        layout = QHBoxLayout(content)
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(70)  # Adjust this value as needed
        self.setFixedWidth(70)  # Adjust this value as needed
        self.setStyleSheet("QScrollArea { border: none; }")

    def setText(self, text):
        self.label.setText(text)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartTagger Tool")
        self.setGeometry(100, 100, 1400, 800)  # Increased width to accommodate new layout

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.current_image_path = None
        self.box_labels = {}  # Dictionary to store labels for each image
        self.polygon_labels = {}
        self.point_labels = {}

        self.class_names = {}  # Dictionary to store class names
        self.class_colors = {}  # Dictionary to store class colors

        # Initialize ImageView before setting up UI
        self.image_view = ImageView()
        self.image_view.setMouseTracking(True)

        self.setup_ui()
        self.setup_connections()

        self.current_tab_index = 0  # Add current tab index tracking

        self.toggle_all_box_button = None
        self.toggle_all_polygon_button = None
        self.toggle_all_point_button = None

        self.add_shortcut(self.show_add_label_dialog, 'W', self.show_add_label_dialog)
        self.add_shortcut(self.delete_label, 'D', self.delete_label)
        self.add_shortcut(self.save, "Ctrl+S", self.save)

        # Set a fixed seed for color generation
        random.seed(42)

    def add_shortcut(self, widget, key, callback):
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(callback)
        # Optionally update the widget's text to show the shortcut
        if isinstance(widget, QPushButton):
            widget.setText(f"{widget.text()} ({key})")

    def setup_connections(self):
        self.image_view.label_selected.connect(self.on_image_label_selected)
        self.polygon_labels_list.itemClicked.connect(self.on_polygon_label_item_clicked)
        self.box_labels_list.itemClicked.connect(self.on_box_label_item_clicked)
        self.point_labels_list.itemClicked.connect(self.on_point_label_item_clicked)
        self.image_view.label_added.connect(self.handle_new_label)
        self.image_view.sam_segmentation_performed.connect(self.handle_sam_segmentation)

    def setup_ui(self):
        # Main layout
        main_splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(main_splitter)

        # Left side: New buttons
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.setup_left_buttons(left_layout)

        # Center: Image view and original buttons
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)

        center_layout.addWidget(self.image_view)

        self.setup_center_buttons(center_layout)

        # Right side: Label list and File list
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Create tab widget for labels
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # All Labels Tab
        all_labels_widget = QWidget()
        all_labels_layout = QVBoxLayout(all_labels_widget)
        all_labels_layout.addWidget(QLabel("All Labels:"))
        self.all_labels_list = QListWidget()
        all_labels_layout.addWidget(self.all_labels_list)
        self.tab_widget.addTab(all_labels_widget, "All")

        # Point Labels Tab
        point_labels_widget = QWidget()
        point_labels_layout = QVBoxLayout(point_labels_widget)
        point_labels_layout.addWidget(QLabel("Point Labels:"))
        self.point_labels_list = QListWidget()
        point_labels_layout.addWidget(self.point_labels_list)
        self.toggle_all_point_button = QPushButton("Toggle All Point Labels")
        self.toggle_all_point_button.clicked.connect(lambda: self.toggle_all_labels('point'))
        point_labels_layout.addWidget(self.toggle_all_point_button)
        self.tab_widget.addTab(point_labels_widget, "Point")

        # Box Labels Tab (original position)
        box_labels_widget = QWidget()
        box_labels_layout = QVBoxLayout(box_labels_widget)
        box_labels_layout.addWidget(QLabel("Box Labels:"))
        self.box_labels_list = QListWidget()
        box_labels_layout.addWidget(self.box_labels_list)
        self.toggle_all_box_button = QPushButton("Toggle All Box Labels")
        self.toggle_all_box_button.clicked.connect(lambda: self.toggle_all_labels('box'))
        box_labels_layout.addWidget(self.toggle_all_box_button)
        self.tab_widget.addTab(box_labels_widget, "Box")

        # Polygon Labels Tab
        polygon_labels_widget = QWidget()
        polygon_labels_layout = QVBoxLayout(polygon_labels_widget)
        polygon_labels_layout.addWidget(QLabel("Polygon Labels:"))
        self.polygon_labels_list = QListWidget()
        polygon_labels_layout.addWidget(self.polygon_labels_list)
        self.toggle_all_polygon_button = QPushButton("Toggle All Polygon Labels")
        self.toggle_all_polygon_button.clicked.connect(lambda: self.toggle_all_labels('polygon'))
        polygon_labels_layout.addWidget(self.toggle_all_polygon_button)
        self.tab_widget.addTab(polygon_labels_widget, "Polygon")

        # Add tab widget to the right layout
        right_layout.addWidget(self.tab_widget)

        # File list
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        file_layout.addWidget(QLabel("Files:"))
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list)

        # Create a splitter for the right side
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self.tab_widget)
        right_splitter.addWidget(file_widget)
        right_layout.addWidget(right_splitter)

        # Add widgets to main splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(center_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(0, 1)  # Left buttons
        main_splitter.setStretchFactor(1, 3)  # Image view takes more space
        main_splitter.setStretchFactor(2, 1)  # Right side

        # Connect signals
        self.file_list.currentItemChanged.connect(self.change_image)

    def on_tab_changed(self, index):
        """Handle tab switching event"""
        tab_text = self.tab_widget.tabText(index)

        if tab_text == "All":
            self.image_view.set_active_label_type(None)
            self.update_all_labels_list()
        elif tab_text in ["Point", "Box", "Polygon"]:
            label_type = tab_text.lower()
            self.image_view.set_active_label_type(label_type)
            self.update_label_list(label_type)

        self.image_view.update()

    def refresh_active_label_list(self):
        current_tab_index = self.tab_widget.currentIndex()
        tab_text = self.tab_widget.tabText(current_tab_index)

        if tab_text == "All":
            self.update_all_labels_list()
        elif tab_text in ["Point", "Box", "Polygon"]:
            label_type = tab_text.lower()
            self.update_label_list(label_type)

        self.image_view.update()

    def setup_left_buttons(self, layout):
        buttons = [
            ("Add Label (W)", self.show_add_label_dialog),
            ("Delete Label (D)", self.delete_label),
            ("Perform SAM Segmentation", self.perform_sam_segmentation),
            ("Perform YOLO Segmentation", self.perform_yolo_segmentation),
        ]

        for text, callback in buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)

            button.setFixedHeight(100)

            layout.addWidget(button)

            # If it is the SAM button, set its initial state to disabled
            if text == "Perform SAM Segmentation":
                self.sam_button = button

        # Add SAM weight file selection
        sam_layout = QHBoxLayout()
        sam_layout.addWidget(QLabel("SAM:"))
        self.sam_weight_label = ScrollableLabel("/weights/sam2_b.pt")
        sam_layout.addWidget(self.sam_weight_label)
        sam_button = QPushButton("Select")
        sam_button.clicked.connect(self.select_sam_weight)
        sam_layout.addWidget(sam_button)
        layout.addLayout(sam_layout)

        # Add YOLO weight file selection
        yolo_layout = QHBoxLayout()
        yolo_layout.addWidget(QLabel("YOLO:"))
        self.yolo_weight_label = ScrollableLabel("/weights/yolo11n.pt")
        yolo_layout.addWidget(self.yolo_weight_label)
        yolo_button = QPushButton("Select")
        yolo_button.clicked.connect(self.select_yolo_weight)
        yolo_layout.addWidget(yolo_button)
        layout.addLayout(yolo_layout)

        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Confidence:"))
        self.conf_threshold = QLineEdit("0.25")  # Default value
        self.conf_threshold.setFixedWidth(50)
        conf_layout.addWidget(self.conf_threshold)
        layout.addLayout(conf_layout)

        layout.addStretch(1)  # Add stretch to push buttons to the top


    def create_file_selector(self, label, callback):
        layout = QHBoxLayout()
        layout.addWidget(QLabel(f"{label}:"))
        weight_label = ScrollableLabel(f"../weights/{label.lower()}_weight.pt")
        layout.addWidget(weight_label)
        select_button = QPushButton("Select")
        select_button.clicked.connect(callback)
        layout.addWidget(select_button)

        # Create a container widget to hold this layout
        container = QWidget()
        container.setLayout(layout)
        return container

    def get_relative_path(self, path):
        return os.path.relpath(path, os.getcwd())

    def select_sam_weight(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select SAM Weight File", "", "Weight Files (*.pt)")
        if file_path:
            relative_path = self.get_relative_path(file_path)
            self.sam_weight_label.setText(relative_path)

    def select_yolo_weight(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select YOLO Weight File", "", "Weight Files (*.pt)")
        if file_path:
            relative_path = self.get_relative_path(file_path)
            self.yolo_weight_label.setText(relative_path)

    def setup_center_buttons(self, layout):
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)

        buttons = [
            ("Load Images", self.load_images),
            ("Load Folder", self.load_folder),
            ("Load Labels", self.load_labels),
            ("Save (Ctrl+S)", self.save)
        ]

        for text, callback in buttons:
            button = QPushButton(text)
            button.clicked.connect(callback)
            button_layout.addWidget(button)


    def load_images(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Images (*.png *.jpg *.bmp)")
        if file_dialog.exec():
            file_names = file_dialog.selectedFiles()
            self.add_files_to_list(file_names)

    def load_folder(self):
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.Directory)
        if folder_dialog.exec():
            folder_path = folder_dialog.selectedFiles()[0]
            image_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                        image_files.append(os.path.join(root, file))
            self.add_files_to_list(image_files)

    def add_files_to_list(self, file_names):
        self.file_list.clear()
        self.file_list.addItems(file_names)

    def change_image(self, current, previous):
        if current:
            self.current_image_path = current.text()
            self.image_view.load_image(self.current_image_path)
            self.load_image_labels(self.current_image_path)
            self.update_label_lists()

    def load_labels(self):
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.Directory)
        if folder_dialog.exec():
            self.label_folder = folder_dialog.selectedFiles()[0]
            class_file_path = os.path.join(self.label_folder, 'classes.txt')
            self.load_class_names(class_file_path)

            box_folder = os.path.join(self.label_folder, 'Box')
            if os.path.exists(box_folder):
                for file_name in os.listdir(box_folder):
                    if file_name.endswith('.txt'):
                        image_name = os.path.splitext(file_name)[0]
                        box_label_path = os.path.join(box_folder, file_name)
                        self.box_labels[image_name] = self.parse_box_label(box_label_path)

            polygon_folder = os.path.join(self.label_folder, 'Polygon')
            if os.path.exists(polygon_folder):
                for file_name in os.listdir(polygon_folder):
                    if file_name.endswith('.txt'):
                        image_name = os.path.splitext(file_name)[0]
                        polygon_label_path = os.path.join(polygon_folder, file_name)
                        self.polygon_labels[image_name] = self.parse_polygon_label(polygon_label_path)

            point_folder = os.path.join(self.label_folder, 'Point')
            if os.path.exists(point_folder):
                for file_name in os.listdir(point_folder):
                    if file_name.endswith('.txt'):
                        image_name = os.path.splitext(file_name)[0]
                        point_label_path = os.path.join(point_folder, file_name)
                        self.point_labels[image_name] = self.parse_point_label(point_label_path)

            self.update_label_lists()

    def load_class_names(self, class_file_path):
        if os.path.exists(class_file_path):
            with open(class_file_path, 'r') as f:
                self.class_names = {i: name.strip() for i, name in enumerate(f)}
        else:
            self.class_names = {0: '0', 1: '1'}  # Default class names
            self.save_class_names(class_file_path)

        # Generate colors for each class
        for class_id in self.class_names:
            if class_id not in self.class_colors:
                self.class_colors[class_id] = self.generate_random_color(seed=class_id)

    def generate_random_color(self, seed=None):
        if seed is not None:
            random.seed(seed)
        return QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    def parse_point_label(self, label_path):
        labels = []
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 3:
                    class_id, x, y = map(float, parts)
                    labels.append({
                        'class_id': int(class_id),
                        'point': (x, y)
                    })
        # print(labels)
        return labels

    def parse_box_label(self, label_path):
        labels = []
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    class_id, x_center, y_center, width, height = map(float, parts)
                    labels.append({
                        'class_id': int(class_id),
                        'bbox': [x_center, y_center, width, height]
                    })
        return labels

    def parse_polygon_label(self, label_path):
        labels = []
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 3 and len(parts) % 2 == 1:
                    class_id = int(parts[0])
                    points = list(map(float, parts[1:]))
                    polygon = [(points[i], points[i + 1]) for i in range(0, len(points), 2)]
                    labels.append({
                        'class_id': class_id,
                        'polygon': polygon
                    })
        return labels

    def load_image_labels(self, image_path):
        image_name = os.path.splitext(os.path.basename(image_path))[0]

        box_labels = self.box_labels.get(image_name, [])
        polygon_labels = self.polygon_labels.get(image_name, [])
        point_labels = self.point_labels.get(image_name, [])

        # Reset visualization options
        self.label_visibility = {
            'box': set(range(len(box_labels))),
            'polygon': set(range(len(polygon_labels))),
            'point': set(range(len(point_labels)))
        }

        self.image_view.set_labels(box_labels, polygon_labels, point_labels,
                                   self.class_colors, self.class_names)

        self.update_all_labels_list()
        self.update_label_list('box')
        self.update_label_list('polygon')
        self.update_label_list('point')

    def update_label_list(self, label_type):
        list_widget = getattr(self, f"{label_type}_labels_list")
        list_widget.clear()

        if self.current_image_path:
            image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
            labels = getattr(self, f"{label_type}_labels").get(image_name, [])

            for i, label in enumerate(labels):
                class_id = label['class_id']
                class_name = self.class_names.get(class_id, str(class_id))
                item = QListWidgetItem(list_widget)
                custom_item = CustomListItem(f"{class_name} ({label_type.capitalize()} Label {i})", i, label_type)
                item.setSizeHint(custom_item.sizeHint())
                list_widget.setItemWidget(item, custom_item)

                custom_item.visibility_changed.connect(self.toggle_label_visibility)

                # Set initial visibility state
                is_visible = i in self.label_visibility[label_type]
                custom_item.checkbox.setChecked(is_visible)

        # 重新连接信号
        list_widget.itemClicked.connect(getattr(self, f"on_{label_type}_label_item_clicked"))

    def update_visible_labels(self, label_type):
        """更新标签可见性"""
        if not self.current_image_path:
            return

        # Clear visibility for all labels
        self.image_view.visible_box_labels.clear()
        self.image_view.visible_polygon_labels.clear()
        self.image_view.visible_point_labels.clear()

        # Display only the current type of labels
        image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        if label_type == 'box' and image_name in self.box_labels:
            self.image_view.visible_box_labels = set(range(len(self.box_labels[image_name])))
        elif label_type == 'polygon' and image_name in self.polygon_labels:
            self.image_view.visible_polygon_labels = set(range(len(self.polygon_labels[image_name])))
        elif label_type == 'point' and image_name in self.point_labels:
            self.image_view.visible_point_labels = set(range(len(self.point_labels[image_name])))

        self.image_view.update()

    def update_label_lists(self):
        self.update_box_label_list()
        self.update_polygon_label_list()
        self.update_point_label_list()
        self.update_all_labels_list()

    def update_point_label_list(self):
        self.point_labels_list.clear()
        if self.current_image_path:
            image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
            if image_name in self.point_labels:
                for i, label in enumerate(self.point_labels[image_name]):
                    class_id = label['class_id']
                    class_name = self.class_names.get(class_id, str(class_id))
                    item = QListWidgetItem(self.point_labels_list)
                    custom_item = CustomListItem(f"{class_name} (Point Label {i})", i, 'point')
                    item.setSizeHint(custom_item.sizeHint())
                    self.point_labels_list.setItemWidget(item, custom_item)
                    custom_item.visibility_changed.connect(self.toggle_label_visibility)
        self.point_labels_list.itemClicked.connect(self.on_point_label_item_clicked)

    def update_box_label_list(self):
        self.box_labels_list.clear()
        if self.current_image_path:
            image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
            if image_name in self.box_labels:
                for i, label in enumerate(self.box_labels[image_name]):
                    class_id = label['class_id']
                    class_name = self.class_names.get(class_id, str(class_id))
                    item = QListWidgetItem(self.box_labels_list)
                    custom_item = CustomListItem(f"{class_name} (Box Label {i})", i, 'box')
                    item.setSizeHint(custom_item.sizeHint())
                    self.box_labels_list.setItemWidget(item, custom_item)
                    custom_item.visibility_changed.connect(self.toggle_label_visibility)
        self.box_labels_list.itemClicked.connect(self.on_box_label_item_clicked)

    def update_polygon_label_list(self):
        self.polygon_labels_list.clear()
        if self.current_image_path:
            image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
            if image_name in self.polygon_labels:
                for i, label in enumerate(self.polygon_labels[image_name]):
                    class_id = label['class_id']
                    class_name = self.class_names.get(class_id, str(class_id))
                    item = QListWidgetItem(self.polygon_labels_list)
                    custom_item = CustomListItem(f"{class_name} (Polygon Label {i})", i, 'polygon')
                    item.setSizeHint(custom_item.sizeHint())
                    self.polygon_labels_list.setItemWidget(item, custom_item)
                    custom_item.visibility_changed.connect(self.toggle_label_visibility)
        self.polygon_labels_list.itemClicked.connect(self.on_polygon_label_item_clicked)

    def update_all_labels_list(self):
        self.all_labels_list.clear()

        if self.current_image_path:
            image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
            for label_type in ['box', 'polygon', 'point']:
                labels = getattr(self, f"{label_type}_labels").get(image_name, [])
                for i, label in enumerate(labels):
                    class_id = label['class_id']
                    class_name = self.class_names.get(class_id, str(class_id))
                    item = QListWidgetItem(self.all_labels_list)
                    custom_item = CustomListItem(f"{class_name} ({label_type.capitalize()} Label {i})", i, label_type)
                    item.setSizeHint(custom_item.sizeHint())
                    self.all_labels_list.setItemWidget(item, custom_item)

                    custom_item.visibility_changed.connect(self.toggle_label_visibility)

                    # Set initial visibility state
                    is_visible = i in self.label_visibility[label_type]
                    custom_item.checkbox.setChecked(is_visible)

        # Reconnect signals
        self.all_labels_list.itemClicked.connect(self.on_all_label_item_clicked)

    def toggle_label_visibility(self, label_index, is_visible, label_type):
        if is_visible:
            self.label_visibility[label_type].add(label_index)
        else:
            self.label_visibility[label_type].discard(label_index)

        self.image_view.set_label_visibility(label_index, is_visible, label_type)
        self.image_view.update()

        # Update the corresponding individual list
        list_widget = getattr(self, f"{label_type}_labels_list")
        if list_widget:
            item = list_widget.item(label_index)
            if item:
                custom_item = list_widget.itemWidget(item)
                custom_item.checkbox.setChecked(is_visible)

        # Update the all_labels list
        for i in range(self.all_labels_list.count()):
            item = self.all_labels_list.item(i)
            custom_item = self.all_labels_list.itemWidget(item)
            if custom_item.label_type == label_type and custom_item.index == label_index:
                custom_item.checkbox.setChecked(is_visible)
                break

    def toggle_polygon_label_visibility(self, label_index, is_visible):
        self.toggle_label_visibility(label_index, is_visible, 'polygon')

    def toggle_all_labels(self, label_type):
        if label_type == 'box':
            labels_list = self.box_labels_list
        elif label_type == 'polygon':
            labels_list = self.polygon_labels_list
        elif label_type == 'point':
            labels_list = self.point_labels_list
        else:
            return

        # Check if all are currently selected
        all_checked = all(labels_list.itemWidget(labels_list.item(i)).checkbox.isChecked()
                          for i in range(labels_list.count()))

        # Toggle the state of all items
        for i in range(labels_list.count()):
            custom_item = labels_list.itemWidget(labels_list.item(i))
            custom_item.checkbox.setChecked(not all_checked)
            custom_item.on_checkbox_clicked()

    def on_point_label_item_clicked(self, item):
        if self.image_view.active_label_type in [None, 'point']:
            label_index = self.point_labels_list.row(item)
            if self.image_view.selected_point_label != label_index:
                self.image_view.set_selected_label(label_index, 'point')

    def on_polygon_label_item_clicked(self, item):
        if self.image_view.active_label_type in [None, 'polygon']:
            label_index = self.polygon_labels_list.row(item)
            if self.image_view.selected_polygon_label != label_index:
                self.image_view.set_selected_label(label_index, 'polygon')

    def on_box_label_item_clicked(self, item):
        if self.image_view.active_label_type in [None, 'box']:
            label_index = self.box_labels_list.row(item)
            if self.image_view.selected_box_label != label_index:
                self.image_view.set_selected_label(label_index, 'box')

    def on_all_label_item_clicked(self, item):
        custom_item = self.all_labels_list.itemWidget(item)
        label_type = custom_item.label_type
        label_index = custom_item.index

        self.image_view.set_selected_label(label_index, label_type)

        # Update the selection state of the corresponding individual list
        list_widget = getattr(self, f"{label_type}_labels_list")
        if list_widget:
            list_widget.setCurrentRow(label_index)

    def on_image_label_selected(self, index, label_type):
        if label_type == 'box':
            self.box_labels_list.setCurrentRow(index)
            self.selected_label = {'type': 'Box', 'index': index}
        elif label_type == 'polygon':
            self.polygon_labels_list.setCurrentRow(index)
            self.selected_label = {'type': 'Polygon', 'index': index}
        elif label_type == 'point':
            self.point_labels_list.setCurrentRow(index)
            self.selected_label = {'type': 'Point', 'index': index}
        elif label_type == 'none':
            self.box_labels_list.clearSelection()
            self.polygon_labels_list.clearSelection()
            self.point_labels_list.clearSelection()
            self.selected_label = None

        # Update the selection of all labels list
        self.update_all_labels_list_selection(index, label_type)
        self.image_view.update()

    def update_all_labels_list_selection(self, index, label_type):
        for i in range(self.all_labels_list.count()):
            item = self.all_labels_list.item(i)
            custom_item = self.all_labels_list.itemWidget(item)
            if custom_item.label_type == label_type and custom_item.index == index:
                self.all_labels_list.setCurrentItem(item)
                break
        else:
            self.all_labels_list.clearSelection()

    def update_selected_label_in_list(self, selected_index, label_type='box'):
        if label_type == 'box':
            label_list = self.box_labels_list
        else:
            label_list = self.polygon_labels_list

        for i in range(label_list.count()):
            item = label_list.item(i)
            custom_item = label_list.itemWidget(item)
            if i == selected_index:
                item.setSelected(True)
                custom_item.setStyleSheet("background-color: lightblue;")
            else:
                item.setSelected(False)
                custom_item.setStyleSheet("")

    def handle_sam_segmentation(self, label_type, points):
        if not self.current_image_path:
            QMessageBox.warning(self, "Warning", "No image selected.")
            return

        self.save(skipDialog=True)

        sam_weight = os.path.abspath(self.sam_weight_label.label.text())
        conf_threshold = float(self.conf_threshold.text())
        image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]

        class_id = self.select_class(is_sam=True)
        if class_id == -1:  # User canceled the selection
            return

        if label_type.lower() == 'box':
            result = self.perform_sam_with_add_boxes(image_name, points, class_id,
                                                     sam_weight=sam_weight, conf=conf_threshold)
        elif label_type.lower() == 'point':
            result = self.perform_sam_with_add_points(image_name, points, class_id,
                                                      sam_weight=sam_weight, conf=conf_threshold)
        else:
            QMessageBox.warning(self, "Warning", "Unsupported label type for SAM segmentation.")
            return

        # Handle the result
        if result and result["status"] == "success":
            QMessageBox.information(self, "Success", result["message"])
            self.refresh_labels()
        else:
            QMessageBox.warning(self, "Error", "SAM segmentation failed.")

    def perform_sam_with_add_boxes(self, image_name, points, class_id, sam_weight, conf):
        if len(points) != 2:
            QMessageBox.warning(self, "Warning", "Invalid box coordinates.")
            return

        # Convert points to bbox format
        x1, y1 = points[0]
        x2, y2 = points[1]
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        bbox = {'class_id': class_id, 'bbox': [center_x, center_y, width, height]}

        return SAMProcessor.process(self.current_image_path, [bbox], self.label_folder, 'box',
                                    reduction_factor=4, iou_threshold=0.6, model_path=sam_weight, conf=conf)

    def perform_sam_with_add_points(self, image_name, points, class_id, sam_weight, conf):
        if not points:
            QMessageBox.warning(self, "Warning", "No points found.")
            return

        # 将点转换为所需的格式
        point_labels = [{'class_id': class_id, 'point': point} for point in points]

        return SAMProcessor.process(self.current_image_path, point_labels, self.label_folder, 'point',
                                    reduction_factor=4, iou_threshold=0.6, model_path=sam_weight, conf=conf)

    def perform_sam_segmentation(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "Warning", "No image selected.")
            return

        image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        conf_threshold = float(self.conf_threshold.text())
        sam_weight = os.path.abspath(self.sam_weight_label.label.text())

        self.save(skipDialog=True)

        if self.image_view.active_label_type == 'box':
            result = self.perform_sam_with_boxes(image_name, sam_weight=sam_weight, conf=conf_threshold)
        elif self.image_view.active_label_type == 'point':
            result = self.perform_sam_with_points(image_name, sam_weight=sam_weight, conf=conf_threshold)
        else:
            QMessageBox.warning(self, "Warning", "Please select point or box labels for SAM segmentation.")
            return

        # 处理结果
        if result["status"] == "success":
            QMessageBox.information(self, "Success", result["message"])
            self.refresh_labels()
        else:
            QMessageBox.warning(self, "Error", "SAM segmentation failed.")

    def perform_sam_with_boxes(self, image_name, sam_weight, conf):
        if image_name not in self.box_labels:
            QMessageBox.warning(self, "Warning", "No box labels found for the current image.")
            return

        visible_labels = []
        for i, label in enumerate(self.box_labels[image_name]):
            item = self.box_labels_list.item(i)
            custom_item = self.box_labels_list.itemWidget(item)
            if custom_item.checkbox.isChecked():
                visible_labels.append(label)

        if not visible_labels:
            QMessageBox.warning(self, "Warning", "No visible box labels found.")
            return

        return SAMProcessor.process(self.current_image_path, visible_labels, self.label_folder, 'box',
                                    reduction_factor=4, iou_threshold=0.6, model_path=sam_weight, conf=conf)

    def perform_sam_with_points(self, image_name, sam_weight, conf):
        if image_name not in self.point_labels:
            QMessageBox.warning(self, "Warning", "No point labels found for the current image.")
            return

        visible_labels = []
        for i, label in enumerate(self.point_labels[image_name]):
            item = self.point_labels_list.item(i)
            custom_item = self.point_labels_list.itemWidget(item)
            if custom_item.checkbox.isChecked():
                visible_labels.append(label)

        if not visible_labels:
            QMessageBox.warning(self, "Warning", "No visible point labels found.")
            return

        return SAMProcessor.process(self.current_image_path, visible_labels, self.label_folder, 'point',
                                    reduction_factor=4, iou_threshold=0.6, model_path=sam_weight, conf=conf)

    def refresh_labels(self):
        if self.label_folder and self.current_image_path:
            # Clear existing labels
            self.box_labels.clear()
            self.polygon_labels.clear()
            self.point_labels.clear()

            # Reload category names
            self.load_class_names(os.path.join(self.label_folder, 'classes.txt'))

            # Load box labels
            box_folder = os.path.join(self.label_folder, 'Box')
            if os.path.exists(box_folder):
                for file_name in os.listdir(box_folder):
                    if file_name.endswith('.txt'):
                        image_name = os.path.splitext(file_name)[0]
                        box_label_path = os.path.join(box_folder, file_name)
                        self.box_labels[image_name] = self.parse_box_label(box_label_path)

            # Load polygon labels
            polygon_folder = os.path.join(self.label_folder, 'Polygon')
            if os.path.exists(polygon_folder):
                for file_name in os.listdir(polygon_folder):
                    if file_name.endswith('.txt'):
                        image_name = os.path.splitext(file_name)[0]
                        polygon_label_path = os.path.join(polygon_folder, file_name)
                        self.polygon_labels[image_name] = self.parse_polygon_label(polygon_label_path)

            # Load point labels
            point_folder = os.path.join(self.label_folder, 'Point')
            if os.path.exists(point_folder):
                for file_name in os.listdir(point_folder):
                    if file_name.endswith('.txt'):
                        image_name = os.path.splitext(file_name)[0]
                        point_label_path = os.path.join(point_folder, file_name)
                        self.point_labels[image_name] = self.parse_point_label(point_label_path)

            # Simulate image switching process
            self.image_view.load_image(self.current_image_path)
            self.load_image_labels(self.current_image_path)

            self.update_label_lists()

        # Update the current item in the file list
        current_image_name = os.path.basename(self.current_image_path)
        items = self.file_list.findItems(current_image_name, Qt.MatchExactly)
        if items:
            self.file_list.setCurrentItem(items[0])

    def show_add_label_dialog(self):
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Label")
        layout = QVBoxLayout(dialog)

        label_type_group = QButtonGroup(dialog)
        normal_radio = QRadioButton("Normal Label")
        sam_radio = QRadioButton("SAM Label")
        label_type_group.addButton(normal_radio)
        label_type_group.addButton(sam_radio)
        layout.addWidget(normal_radio)
        layout.addWidget(sam_radio)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        if dialog.exec_() == QDialog.Accepted:
            if normal_radio.isChecked():
                self.show_normal_label_options()
            elif sam_radio.isChecked():
                self.show_sam_label_options()

    def show_normal_label_options(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Normal Label Options")
        layout = QVBoxLayout(dialog)

        options = ["Point", "Box", "Polygon"]
        for option in options:
            button = QPushButton(option)
            button.clicked.connect(lambda checked, o=option: self.start_drawing_label(o, dialog, is_sam=False))
            layout.addWidget(button)

        dialog.exec()

    def start_drawing_label(self, label_type, dialog, is_sam=False):
        self.image_view.start_drawing(label_type, is_sam)
        dialog.accept()  # This will close the dialog

    def show_sam_label_options(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("SAM Label Options")
        layout = QVBoxLayout(dialog)

        options = ["Point", "Box"]
        for option in options:
            button = QPushButton(option)
            button.clicked.connect(lambda checked, o=option: self.start_drawing_label(o, dialog, is_sam=True))
            layout.addWidget(button)

        dialog.exec_()

    def add_new_label(self, label_type, points, class_id):
        if not self.current_image_path:
            return

        image_name = os.path.splitext(os.path.basename(self.current_image_path))[0]

        if label_type == "Point":
            new_label = {'class_id': class_id, 'point': points[0]}
            if image_name not in self.point_labels:
                self.point_labels[image_name] = []
            self.point_labels[image_name].append(new_label)
        elif label_type == "Box":
            x1, y1 = points[0]
            x2, y2 = points[1]
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            new_label = {'class_id': class_id, 'bbox': [center_x, center_y, width, height]}
            if image_name not in self.box_labels:
                self.box_labels[image_name] = []
            self.box_labels[image_name].append(new_label)
        elif label_type == "Polygon":
            new_label = {'class_id': class_id, 'polygon': points}
            if image_name not in self.polygon_labels:
                self.polygon_labels[image_name] = []
            self.polygon_labels[image_name].append(new_label)

        self.update_label_lists()
        self.image_view.update()

    def start_drawing(self, label_type, is_sam=False):
        self.image_view.start_drawing(label_type, is_sam)

    def handle_new_label(self, label_type, points):
        class_id = self.select_class(is_sam=False)
        if label_type == "Point":
            self.add_new_label("Point", points, class_id)
        elif label_type == "Box":
            self.add_new_label("Box", points, class_id)
        elif label_type == "Polygon":
            self.add_new_label("Polygon", points, class_id)

        # Update UI
        self.update_label_lists()
        self.image_view.update()

    def select_class(self, is_sam=False):
        class_dialog = QDialog(self)
        class_dialog.setWindowTitle("Select Class")
        layout = QVBoxLayout()

        class_combo = QComboBox()
        class_combo.addItems(self.class_names.values())
        layout.addWidget(class_combo)

        new_class_input = QLineEdit()
        new_class_input.setPlaceholderText("Enter new class name")
        layout.addWidget(new_class_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        class_dialog.setLayout(layout)

        button_box.accepted.connect(class_dialog.accept)
        button_box.rejected.connect(class_dialog.reject)

        if class_dialog.exec() == QDialog.Accepted:
            if new_class_input.text():
                new_class = new_class_input.text()
                self.add_new_class(new_class)
                return max(self.class_names.keys())  # Return the new class ID
            else:
                return list(self.class_names.keys())[class_combo.currentIndex()]
        else:
            return -1  # User canceled the selection

    def add_new_class(self, new_class):
        if new_class not in self.class_names.values():
            new_id = max(self.class_names.keys()) + 1 if self.class_names else 0
            self.class_names[new_id] = new_class
            self.class_colors[new_id] = self.generate_random_color(seed=new_id)
            if self.label_folder:
                self.save_class_names(os.path.join(self.label_folder, 'classes.txt'))
                # Update UI
                self.update_label_lists()
                self.image_view.update()

    def save_class_names(self, class_file_path=None):
        if class_file_path is None:
            class_file_path = os.path.join(self.label_folder, 'classes.txt')

        with open(class_file_path, 'w') as f:
            if isinstance(self.class_names, dict):
                # If class_names is a dictionary, write id and name
                for class_id, class_name in sorted(self.class_names.items()):
                    f.write(f"{class_name}\n")
            else:
                # If class_names is a list or any other iterable, write just the names
                for class_name in self.class_names:
                    f.write(f"{class_name}\n")

    def save_label(self, label_type, class_id, points):
        if self.current_image not in self.point_labels:
            self.point_labels[self.current_image] = []
        if self.current_image not in self.box_labels:
            self.box_labels[self.current_image] = []
        if self.current_image not in self.polygon_labels:
            self.polygon_labels[self.current_image] = []

        if label_type == "Point":
            self.point_labels[self.current_image].append({'class_id': class_id, 'point': points[0]})
        elif label_type == "Box":
            x1, y1 = points[0]
            x2, y2 = points[1]
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            self.box_labels[self.current_image].append(
                {'class_id': class_id, 'bbox': [center_x, center_y, width, height]})
        elif label_type == "Polygon":
            self.polygon_labels[self.current_image].append({'class_id': class_id, 'polygon': points})

        self.update_label_lists()

    def delete_label(self):
        if hasattr(self, 'selected_label') and self.selected_label:
            label_type = self.selected_label['type']
            index = self.selected_label['index']
            current_image = os.path.splitext(os.path.basename(self.current_image_path))[0]

            if label_type == 'Point':
                if current_image in self.point_labels and 0 <= index < len(self.point_labels[current_image]):
                    del self.point_labels[current_image][index]
            elif label_type == 'Box':
                if current_image in self.box_labels and 0 <= index < len(self.box_labels[current_image]):
                    del self.box_labels[current_image][index]
            elif label_type == 'Polygon':
                if current_image in self.polygon_labels and 0 <= index < len(self.polygon_labels[current_image]):
                    del self.polygon_labels[current_image][index]

            # 更新 UI
            self.update_label_lists()
            self.image_view.update()
            self.selected_label = None
        else:
            QMessageBox.warning(self, "Warning", "No label selected for deletion.")


    def save(self, skipDialog=False):
        if not self.label_folder:
            QMessageBox.warning(self, "Warning", "No label folder selected.")
            return

        # 保存 Box 标签
        box_folder = os.path.join(self.label_folder, 'Box')
        os.makedirs(box_folder, exist_ok=True)
        for image_name, boxes in self.box_labels.items():
            box_file_path = os.path.join(box_folder, f"{image_name}.txt")
            with open(box_file_path, 'w') as f:
                for box in boxes:
                    f.write(f"{box['class_id']} {' '.join(map(str, box['bbox']))}\n")

        # 保存 Polygon 标签
        polygon_folder = os.path.join(self.label_folder, 'Polygon')
        os.makedirs(polygon_folder, exist_ok=True)
        for image_name, polygons in self.polygon_labels.items():
            polygon_file_path = os.path.join(polygon_folder, f"{image_name}.txt")
            with open(polygon_file_path, 'w') as f:
                for polygon in polygons:
                    coords = ' '.join(map(str, [coord for point in polygon['polygon'] for coord in point]))
                    f.write(f"{polygon['class_id']} {coords}\n")

        # 保存 Point 标签
        point_folder = os.path.join(self.label_folder, 'Point')
        os.makedirs(point_folder, exist_ok=True)
        for image_name, points in self.point_labels.items():
            point_file_path = os.path.join(point_folder, f"{image_name}.txt")
            with open(point_file_path, 'w') as f:
                for point in points:
                    f.write(f"{point['class_id']} {point['point'][0]} {point['point'][1]}\n")
        if not skipDialog:
            QMessageBox.information(self, "Success", "Labels saved successfully.")

    def perform_yolo_segmentation(self):
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            QMessageBox.warning(self, "Warning", "No image selected.")
            return

        self.save(skipDialog=True)

        yolo_weight = os.path.abspath(self.yolo_weight_label.label.text())
        conf_threshold = float(self.conf_threshold.text())
        iou_threshold = 0.45  # You can add an input for this in the UI if needed

        # Initialize YOLO processor
        yolo_processor = YOLOProcessor(yolo_weight, conf_threshold, iou_threshold)

        # Process image
        results, img_size = yolo_processor.process_image(self.current_image_path)

        # Process results
        current_image = os.path.splitext(os.path.basename(self.current_image_path))[0]
        if current_image not in self.box_labels:
            self.box_labels[current_image] = []

        for box in results.boxes.data.tolist():
            center_x, center_y, width, height, conf, class_id = yolo_processor.convert_to_yolo_format(box, img_size)

            # Check if class name exists, if not, add it
            if class_id not in self.class_names:
                new_class_name = f"class_{class_id}"
                self.class_names[class_id] = new_class_name
                self.save_class_names()

            # Check for overlapping boxes
            new_box = [center_x, center_y, width, height]
            is_overlapping = False
            for existing_label in self.box_labels[current_image]:
                existing_box = existing_label['bbox']
                iou = yolo_processor.calculate_iou(new_box, existing_box)
                if iou > iou_threshold:
                    is_overlapping = True
                    break

            if not is_overlapping:
                # Add to box_labels
                self.box_labels[current_image].append({
                    'class_id': class_id,
                    'bbox': new_box,
                    'confidence': conf
                })

        # Save results to txt file
        save_path = os.path.join(self.label_folder, 'Box', f"{current_image}.txt")
        yolo_processor.save_results(save_path, results, img_size)

        # Update UI
        self.update_label_lists()
        self.image_view.update()

        QMessageBox.information(self, "Success", "YOLO segmentation completed and saved.")
