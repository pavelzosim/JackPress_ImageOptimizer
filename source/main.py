import time
import sys
import os
import math
import logging
import subprocess
import webbrowser
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QDialog,
    QVBoxLayout, QTextEdit, QPushButton, QProgressBar, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PIL import Image

import gui_pics_rc  # noqa: F401
from ui_mainwindow import Ui_MainWindow

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Constants
class Constants:
    MIN_QUALITY = 10
    MAX_QUALITY = 95
    OUTPUT_FOLDER = "jackpressed"
    DEFAULT_WIDTH = 1024
    PNG_TOOLS = {'oxipng', 'pngquant'}

# Exceptions
class CompressionError(Exception):
    """Base exception for compression errors"""

class ToolNotFoundError(CompressionError):
    """Raised when compression tool not found"""

class InvalidConfigError(CompressionError):
    """Raised for invalid configuration"""

# Data classes
@dataclass
class CompressionConfig:
    input_dir: Path
    process_png: bool
    process_jpg: bool
    keep_original_size: bool
    target_width: int
    compression_level: int
    png_tool: str
    preserve_alpha: bool

# Strategy Pattern
class CompressionStrategy:
    def process(self, config: CompressionConfig, img: Image.Image, output_path: Path):
        raise NotImplementedError

class PNGCompressionStrategy(CompressionStrategy):
    def process(self, config: CompressionConfig, img: Image.Image, output_path: Path):
        try:
            img.save(output_path, 'PNG', optimize=False)
            self._compress_with_tool(config, output_path)
        except Exception as e:
            logger.error(f"PNG compression failed: {e}")
            raise

    def _compress_with_tool(self, config: CompressionConfig, output_path: Path):
        tool = OxiPNGCompressor() if config.png_tool == 'oxipng' else PNGQuantCompressor()
        tool.compress(config, output_path)

class JPEGCompressionStrategy(CompressionStrategy):
    def process(self, config: CompressionConfig, img: Image.Image, output_path: Path):
        try:
            quality = self._calculate_quality(config.compression_level)
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
        except Exception as e:
            logger.error(f"JPEG compression failed: {e}")
            raise

    def _calculate_quality(self, compression_level: int) -> int:
        compression_level = max(1, min(100, compression_level))
        normalized = (compression_level - 1) / 99
        quality = Constants.MIN_QUALITY + int(normalized**2 * 
                    (Constants.MAX_QUALITY - Constants.MIN_QUALITY))
        return max(Constants.MIN_QUALITY, min(quality, Constants.MAX_QUALITY))

# Compression Tools
class Compressor:
    _TOOL_CACHE = {}

    @classmethod
    def get_tool_path(cls, tool_name: str) -> str:
        if tool_name not in cls._TOOL_CACHE:
            base_dir = Path(__file__).parent
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys._MEIPASS)
            tool_path = str(base_dir / 'tools' / tool_name)
            if not Path(tool_path).exists():
                raise ToolNotFoundError(f"{tool_name} not found in tools directory")
            cls._TOOL_CACHE[tool_name] = tool_path
        return cls._TOOL_CACHE[tool_name]

class OxiPNGCompressor(Compressor):
    def compress(self, config: CompressionConfig, output_path: Path):
        cmd = self._build_command(config, output_path)
        self._run_command(cmd, output_path)

    def _build_command(self, config: CompressionConfig, output_path: Path) -> List[str]:
        oxipng_level = 6 - int((config.compression_level / 100) * 6)
        cmd = [
            self.get_tool_path('oxipng.exe'),
            '--opt', str(oxipng_level),
            '--force',
            str(output_path)
        ]
        if not config.preserve_alpha:
            cmd.extend(['--strip', 'safe'])
        return cmd

    def _run_command(self, cmd: List[str], output_path: Path):
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            text=True
        )
        _, stderr = proc.communicate()

        if proc.returncode != 0:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(f"Compression error: {stderr}")

class PNGQuantCompressor(Compressor):
    def compress(self, config: CompressionConfig, output_path: Path):
        cmd = self._build_command(config, output_path)
        self._run_command(cmd, output_path)

    def _build_command(self, config: CompressionConfig, output_path: Path) -> List[str]:
        quality_min = max(0, config.compression_level - 10)
        quality_max = min(100, config.compression_level)
        return [
            self.get_tool_path('pngquant.exe'),
            '--quality', f'{quality_min}-{quality_max}',
            '--speed', '1' if config.compression_level > 50 else '3',
            '--force',
            '--output', str(output_path),
            str(output_path)
        ]

    def _run_command(self, cmd: List[str], output_path: Path):
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            text=True
        )
        _, stderr = proc.communicate()

        if proc.returncode != 0:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(f"Compression error: {stderr}")

# Image Processing
class ImageProcessor:
    @staticmethod
    def remove_alpha_channel(img: Image.Image) -> Image.Image:
        if img.mode in ('RGBA', 'LA'):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img.convert('RGBA'), mask=img.split()[1])
            return background
        return img.convert("RGB")

    @staticmethod
    def resize_image(img: Image.Image, target_width: int) -> Image.Image:
        if img.width == target_width:
            return img.copy()
        ratio = target_width / img.width
        height = int(img.height * ratio)
        return img.resize((target_width, height), Image.LANCZOS)

# Worker Class
class Worker(QThread):
    progress_updated = pyqtSignal(int)
    file_processed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    eta_updated = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, config: CompressionConfig):
        super().__init__()
        self.config = config
        self._is_canceled = False
        self._strategies = self._init_strategies()

    def _init_strategies(self) -> Dict[str, CompressionStrategy]:
        return {
            '.png': PNGCompressionStrategy(),
            '.jpg': JPEGCompressionStrategy(),
            '.jpeg': JPEGCompressionStrategy()
        }

    def cancel(self):
        self._is_canceled = True

    def run(self):
        try:
            self._validate_config()
            files = self._collect_files()
            total = len(files)
            tracker = ProgressTracker(total)

            with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                futures = {executor.submit(self.process_file, f): f for f in files}
                
                for i, future in enumerate(as_completed(futures)):
                    if self._is_canceled:
                        break
                    
                    future.result()
                    progress = int((i + 1) / total * 100)
                    self.progress_updated.emit(progress)
                    self.eta_updated.emit(tracker.update())

            self.finished.emit()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _validate_config(self):
        if not self.config.input_dir.exists():
            raise InvalidConfigError(f"Directory not found: {self.config.input_dir}")
        if not any([self.config.process_png, self.config.process_jpg]):
            raise InvalidConfigError("No file formats selected")

    def _collect_files(self) -> List[Path]:
        output_folder = self.config.input_dir / Constants.OUTPUT_FOLDER
        extensions = self._get_extensions()
        
        return [
            f for f in self.config.input_dir.rglob('*')
            if output_folder not in f.parents
            and f.suffix.lower() in extensions
        ]

    def _get_extensions(self) -> List[str]:
        extensions = []
        if self.config.process_png:
            extensions.append('.png')
        if self.config.process_jpg:
            extensions.extend(['.jpg', '.jpeg'])
        return extensions

    def process_file(self, file_path: Path):
        try:
            self.file_processed.emit(file_path.name)
            output_path = self._get_output_path(file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with Image.open(file_path) as img:
                processed = self._process_image(img)
                self._save_image(processed, file_path, output_path)

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            raise

    def _get_output_path(self, file_path: Path) -> Path:
        output_dir = self.config.input_dir / Constants.OUTPUT_FOLDER
        return output_dir / file_path.relative_to(self.config.input_dir)

    def _process_image(self, img: Image.Image) -> Image.Image:
        if not self.config.preserve_alpha:
            img = ImageProcessor.remove_alpha_channel(img)
        if not self.config.keep_original_size:
            img = ImageProcessor.resize_image(img, self.config.target_width)
        return img

    def _save_image(self, img: Image.Image, original_path: Path, output_path: Path):
        strategy = self._strategies.get(original_path.suffix.lower())
        if not strategy:
            raise ValueError(f"Unsupported format: {original_path.suffix}")
        strategy.process(self.config, img, output_path)

class ProgressTracker:
    def __init__(self, total: int):
        self.start_time = time.time()
        self.total = total
        self.processed = 0

    def update(self) -> str:
        self.processed += 1
        elapsed = time.time() - self.start_time
        if self.processed == 0:
            return "Calculating..."
        eta = (elapsed / self.processed) * (self.total - self.processed)
        return f"ETA: {time.strftime('%H:%M:%S', time.gmtime(eta))}"

class PowerOfTwoSpinBox(QSpinBox):
    MIN_POWER = 6
    MAX_POWER = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(2**self.MIN_POWER, 2**self.MAX_POWER)
        self.setSingleStep(1)
        self.setValue(1024)

    def stepBy(self, steps: int) -> None:
        current = self.value()
        power = int(math.log2(current))
        new_power = min(max(power + steps, self.MIN_POWER), self.MAX_POWER)
        self.setValue(2 ** new_power)

class ErrorDialog(QDialog):
    """Dialog for displaying error messages"""
    def __init__(self, errors: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Errors")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setPlainText("\n".join(errors))
        
        layout.addWidget(self.text_area)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._worker: Optional[Worker] = None
        self._errors: List[str] = []
        
        self._initialize_ui()
        self._setup_connections()

    def _initialize_ui(self) -> None:
        self.ui.compression_Button.setText("Start Compression")
        self.ui.compression_Button.setEnabled(False)

        self.rescale_spinbox = PowerOfTwoSpinBox()
        parent_widget = self.ui.rescaleWidth_SpinBox.parent()
        self.ui.rescaleWidth_SpinBox.deleteLater()
        self.rescale_spinbox.setParent(parent_widget)
        self.rescale_spinbox.setGeometry(self.ui.rescaleWidth_SpinBox.geometry())
        self.ui.rescaleWidth_SpinBox = self.rescale_spinbox

        self.ui.compressionOXIpng_RadioButton.setToolTip(
            "Lossless compression, good balance of speed/quality\n"
            "Optimizes file structure"
        )

        self.ui.compressionPNGquant_RadioButton.setToolTip(
            "Lossy compression\n"
            "Significantly reduces file size"
        )
        self.ui.PNGCompressionGroup.setEnabled(False)
        self.rescale_spinbox.setEnabled(False)

        self.ui.keepOriginImageSize_CheckBox.setChecked(True)
        self.ui.compressionPNGquant_RadioButton.setChecked(True)
        self.ui.preservaAlpha_CheckBox.setChecked(True)
        self.ui.compressionQuality_Slider.setValue(80)
        self.ui.compressionQuality_SpinBox.setValue(80)

        self.ui.donateLinkText.setText('<a href="https://www.pavelzosim.com">by Pavel Zosim 2025</a>')
        self.ui.donateLinkText.setOpenExternalLinks(True)

    def _setup_connections(self) -> None:
        self.ui.browseFolder_Button.clicked.connect(self._select_folder)
        self.ui.png_CheckBox.stateChanged.connect(self._update_ui_state)
        self.ui.jpg_CheckBox.stateChanged.connect(self._update_ui_state)
        self.ui.compression_Button.clicked.connect(self._toggle_processing)
        self.ui.compressionQuality_Slider.valueChanged.connect(self.ui.compressionQuality_SpinBox.setValue)
        self.ui.compressionQuality_SpinBox.valueChanged.connect(self.ui.compressionQuality_Slider.setValue)
        self.ui.keepOriginImageSize_CheckBox.toggled.connect(self.rescale_spinbox.setDisabled)
        self.ui.donateLinkText.linkActivated.connect(webbrowser.open)

    def _update_ui_state(self) -> None:
        self.ui.PNGCompressionGroup.setEnabled(self.ui.png_CheckBox.isChecked())
        self.ui.compression_Button.setEnabled(
            bool(self.ui.folderPath_TextBrowser.toPlainText()) and 
            (self.ui.png_CheckBox.isChecked() or self.ui.jpg_CheckBox.isChecked())
        )

    def _select_folder(self) -> None:
        if folder := QFileDialog.getExistingDirectory(self, "Select Folder"):
            self.ui.folderPath_TextBrowser.setText(folder)
        self._update_ui_state()

    def _get_config(self) -> CompressionConfig:
        return CompressionConfig(
            input_dir=Path(self.ui.folderPath_TextBrowser.toPlainText()),
            process_png=self.ui.png_CheckBox.isChecked(),
            process_jpg=self.ui.jpg_CheckBox.isChecked(),
            keep_original_size=self.ui.keepOriginImageSize_CheckBox.isChecked(),
            target_width=self.ui.rescaleWidth_SpinBox.value(),
            compression_level=self.ui.compressionQuality_SpinBox.value(),
            png_tool='oxipng' if self.ui.compressionOXIpng_RadioButton.isChecked() else 'pngquant',
            preserve_alpha=self.ui.preservaAlpha_CheckBox.isChecked()
        )

    def _toggle_processing(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self.ui.compression_Button.setText("Start Compression")
        else:
            self._errors.clear()
            self._worker = Worker(self._get_config())
            self._worker.progress_updated.connect(self.ui.compression_ProgressBar.setValue)
            self._worker.file_processed.connect(lambda name: self.ui.statusbar.showMessage(f"Processing: {name}"))
            self._worker.error_occurred.connect(self._errors.append)
            self._worker.finished.connect(self._on_processing_finished)
            self._worker.eta_updated.connect(self.ui.statusbar.showMessage)
            self._worker.start()
            self.ui.compression_Button.setText("Cancel")

    def _on_processing_finished(self) -> None:
        self.ui.compression_Button.setText("Start Compression")
        if self._errors:
            QMessageBox.critical(self, "Error", "\n".join(self._errors))
        else:
            QMessageBox.information(self, "Success", "Batch processing completed successfully.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())