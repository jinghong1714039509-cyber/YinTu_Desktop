import sys
from PySide6.QtWidgets import QApplication, QMainWindow

def main():
    app = QApplication(sys.argv)

    w = QMainWindow()
    w.setWindowTitle("YinTu Desktop - Stage 1 (PySide6 OK)")
    w.resize(900, 600)
    w.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
