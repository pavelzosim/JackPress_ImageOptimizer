# JackPress Image Optimizer

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![Open Source](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://opensource.org/)

A professional GUI tool for batch image optimization and resizing with parallel processing support.

## Features ✨

- **Dual Compression Engines**
  - 🖼️ PNG: oxipng (lossless) / pngquant (lossy)
  - 📸 JPEG: Custom quality mapping
- **Smart Processing**
  - Multi-threaded batch operations
  - Automatic alpha channel handling
  - Power-of-2 resizing (512, 1024, 2048 etc.)
- **Advanced Controls**
  - Real-time progress tracking
  - ETA calculations
  - Error reporting system
- **Presets Management**
  - Custom quality profiles
  - Size preservation options
  - Output directory auto-creation

## Installation 🛠️

### Requirements
- Python 3.8+
- PyQt5
- Pillow

```bash

# Clone repository
git clone https://github.com/yourusername/jackpressed.git

# Install dependencies
pip install PyQt5 Pillow

```
Tools Setup
Place these executables in tools/ folder:

oxipng.exe

pngquant.exe

Usage 🖥️
Select Input Folder
Choose directory with images to process

Configure Settings
UI Preview

Select file formats (PNG/JPG)

Set compression level (1-100)

Choose resizing options

Configure alpha channel handling

Start Processing
Optimized images save to jackpressed/ subdirectory

Configuration Options ⚙️
Parameter	Description	Default
Compression Level	Quality vs file size balance	80
Target Width	Resize to nearest power-of-2	1024
Preserve Alpha	Keep transparency channel	Off
Keep Original Size	Disable resizing	On
PNG Compression Tool	Choose between oxipng/pngquant	pngquant

Technical Highlights 🧠
# Smart quality remapping for JPEG
def _calculate_quality(compression_level: int) -> int:
    normalized = (compression_level - 1) / 99
    return MIN_QUALITY + int(normalized**2 * (MAX_QUALITY - MIN_QUALITY))

License 📄
MIT License - See LICENSE for details.

Developed with ❤️ by Pavel Zosim
Project Website | Donate






    
