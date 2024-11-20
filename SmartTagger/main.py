# -*- coding = utf-8 -*-
# @Time :2024/10/28 18:41
# @Author :Pang
# @File :  main.py
# @Description :


import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
