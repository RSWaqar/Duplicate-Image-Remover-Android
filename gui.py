import sys
import os
import types
import ctypes
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QFileDialog, QLabel, QListWidget, QCheckBox, 
    QListWidgetItem, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QIcon
from PIL import Image
import send2trash

# =============================================
# NUMPY WORKAROUND FOR PYTHON 3.13 COMPATIBILITY
# =============================================
if sys.version_info >= (3, 13):
    # Create fake numpy modules to satisfy imports
    sys.modules['numpy'] = types.ModuleType('numpy')
    sys.modules['numpy.core'] = types.ModuleType('numpy.core')
    sys.modules['numpy.core.overrides'] = types.ModuleType('numpy.core.overrides')
    
    # Create lightweight imagehash replacement
    class SimpleImageHash:
        @staticmethod
        def average_hash(image, hash_size=8):
            """Simplified hash calculation that doesn't require numpy"""
            try:
                from PIL import Image
                # Convert to grayscale and resize
                img = image.convert('L').resize((hash_size, hash_size), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                return ''.join(['1' if pixel > avg else '0' for pixel in pixels])
            except Exception as e:
                return str(abs(hash(image.tobytes())))
    
    sys.modules['imagehash'] = types.ModuleType('imagehash')
    sys.modules['imagehash'].average_hash = SimpleImageHash.average_hash

# ===========================
# PERFORMANCE OPTIMIZATIONS
# ===========================
if sys.platform == 'win32':
    # Faster DLL loading
    ctypes.windll.kernel32.SetDllDirectoryW(None)
    # Higher process priority
    ctypes.windll.kernel32.SetPriorityClass(
        ctypes.windll.kernel32.GetCurrentProcess(), 
        0x00008000  # HIGH_PRIORITY
    )

# PyInstaller runtime fix
if getattr(sys, 'frozen', False):
    os.environ['PATH'] = sys._MEIPASS + ";" + os.environ['PATH']

class DuplicateRemoverApp(QWidget):
    def __init__(self):
        super().__init__()
        self.dark_mode = False
        self.folder_path = ""
        self.duplicates = []
        
        # Set application icon
        self.setWindowIcon(QIcon('app_icon.ico'))
        
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Duplicate Image Remover")
        self.setGeometry(100, 100, 600, 500)

        # Main layout
        self.layout = QVBoxLayout()

        # Theme toggle button at top right
        self.theme_toggle_btn = QPushButton("🌙 Dark Mode")
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        self.theme_toggle_btn.setStyleSheet(self.get_button_style())
        
        # Create a horizontal layout for the top bar
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Duplicate Image Remover"))
        top_layout.addStretch()
        top_layout.addWidget(self.theme_toggle_btn)
        self.layout.addLayout(top_layout)

        self.label = QLabel("Selected Folder: None")
        self.layout.addWidget(self.label)

        self.select_folder_btn = QPushButton("📁 Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)
        self.select_folder_btn.setStyleSheet(self.get_button_style())
        self.layout.addWidget(self.select_folder_btn)

        self.scan_btn = QPushButton("🔍 Scan for Duplicates")
        self.scan_btn.clicked.connect(self.scan_duplicates)
        self.scan_btn.setStyleSheet(self.get_button_style())
        self.layout.addWidget(self.scan_btn)

        self.duplicates_list = QListWidget()
        self.duplicates_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.layout.addWidget(self.duplicates_list)
        
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.stateChanged.connect(self.select_all_items)
        self.layout.addWidget(self.select_all_checkbox)
        
        self.recycle_bin_checkbox = QCheckBox("Move to Recycle Bin Instead of Deleting Permanently")
        self.recycle_bin_checkbox.setChecked(True)
        self.layout.addWidget(self.recycle_bin_checkbox)
        
        self.delete_btn = QPushButton("🗑️ Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setStyleSheet(self.get_button_style(delete_button=True))
        self.layout.addWidget(self.delete_btn)
        
        self.status_label = QLabel("Ready")
        self.layout.addWidget(self.status_label)
        
        self.setLayout(self.layout)
        self.apply_theme()

    def get_button_style(self, delete_button=False):
        """Return appropriate button style based on theme and button type"""
        if delete_button:
            base_color = "#ff4444" if self.dark_mode else "#ff6666"
            hover_color = "#ff2222" if self.dark_mode else "#ff4444"
        else:
            base_color = "#8e2dc5" if self.dark_mode else "#9b59b6"
            hover_color = "#7d1db4" if self.dark_mode else "#8e44ad"
        
        return f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 120px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {base_color};
                padding: 9px 15px 7px 17px;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """
    
    def toggle_theme(self):
        """Switch between light and dark mode"""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.theme_toggle_btn.setText("☀️ Light Mode" if self.dark_mode else "🌙 Dark Mode")
        self.select_folder_btn.setStyleSheet(self.get_button_style())
        self.scan_btn.setStyleSheet(self.get_button_style())
        self.delete_btn.setStyleSheet(self.get_button_style(delete_button=True))
        self.theme_toggle_btn.setStyleSheet(self.get_button_style())
    
    def apply_theme(self):
        """Apply the current theme (light or dark) to the application"""
        palette = QPalette()
        
        if self.dark_mode:
            # Dark theme colors
            palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
            palette.setColor(QPalette.ColorRole.Highlight, QColor(142, 45, 197).lighter())
            palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
            
            # Custom list widget colors
            self.duplicates_list.setStyleSheet(
                "QListWidget { background-color: #252525; color: white; border: 1px solid #444; border-radius: 4px; }"
                "QListWidget::item { padding: 4px; }"
                "QListWidget::item:selected { background-color: #8e2dc5; }"
                "QListWidget::item:hover { background-color: #333; }"
            )
            
            # Checkbox styling
            checkbox_style = """
                QCheckBox { color: white; }
                QCheckBox::indicator { width: 16px; height: 16px; }
            """
            self.select_all_checkbox.setStyleSheet(checkbox_style)
            self.recycle_bin_checkbox.setStyleSheet(checkbox_style)
        else:
            # Light theme colors
            palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
            palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
            palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
            palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
            palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
            palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
            palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
            palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
            palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
            palette.setColor(QPalette.ColorRole.Highlight, QColor(142, 45, 197).lighter())
            palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
            
            # Reset list widget style
            self.duplicates_list.setStyleSheet(
                "QListWidget { background-color: white; color: black; border: 1px solid #ddd; border-radius: 4px; }"
                "QListWidget::item { padding: 4px; }"
                "QListWidget::item:selected { background-color: #9b59b6; color: white; }"
                "QListWidget::item:hover { background-color: #f0f0f0; }"
            )
            
            # Reset checkbox styling
            self.select_all_checkbox.setStyleSheet("")
            self.recycle_bin_checkbox.setStyleSheet("")
        
        self.setPalette(palette)
        QApplication.instance().setPalette(palette)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_path = folder
            self.label.setText(f"Selected Folder: {folder}")
            self.status_label.setText("Ready to scan")
    
    def scan_duplicates(self):
        if not self.folder_path:
            self.label.setText("Please select a folder first!")
            return
        
        self.duplicates_list.clear()
        self.duplicates = []
        self.select_all_checkbox.setChecked(False)
        self.status_label.setText("Scanning...")
        QApplication.processEvents()
        
        hashes = {}
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff')
        
        try:
            for root, _, files in os.walk(self.folder_path):
                for file in files:
                    if file.lower().endswith(image_extensions):
                        file_path = os.path.join(root, file)
                        try:
                            with Image.open(file_path) as img:
                                # Use our patched imagehash function
                                img_hash = str(sys.modules['imagehash'].average_hash(img))
                            
                            if img_hash in hashes:
                                self.duplicates.append(file_path)
                                item = QListWidgetItem(file_path)
                                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                                item.setCheckState(Qt.CheckState.Unchecked)
                                self.duplicates_list.addItem(item)
                            else:
                                hashes[img_hash] = file_path
                        except Exception as e:
                            print(f"Error processing {file_path}: {e}")
            
            if not self.duplicates:
                self.status_label.setText("No duplicates found!")
            else:
                self.status_label.setText(f"Found {len(self.duplicates)} potential duplicates")
        except Exception as e:
            self.status_label.setText(f"Scan error: {str(e)}")
    
    def select_all_items(self, state):
        for i in range(self.duplicates_list.count()):
            item = self.duplicates_list.item(i)
            item.setCheckState(Qt.CheckState.Checked if state == 2 else Qt.CheckState.Unchecked)
    
    def delete_selected(self):
        selected_count = 0
        move_to_recycle = self.recycle_bin_checkbox.isChecked()
        
        for i in range(self.duplicates_list.count()-1, -1, -1):
            item = self.duplicates_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                file_path = os.path.normpath(item.text())
                try:
                    if move_to_recycle:
                        send2trash.send2trash(file_path)
                    else:
                        os.remove(file_path)
                    self.duplicates_list.takeItem(i)
                    selected_count += 1
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        self.status_label.setText(f"Deleted {selected_count} files")
        self.select_all_checkbox.setChecked(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DuplicateRemoverApp()
    window.show()
    sys.exit(app.exec())