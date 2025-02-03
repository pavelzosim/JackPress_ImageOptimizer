# JackPress Image Optimizer
![poster_jackal](https://github.com/user-attachments/assets/26ee2b7b-99a7-4e12-a5b2-222fd87a4e5f)

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


## System Requirements 💻

**Supported OS:**
- Windows 7/8/10/11 (x86/x64)
  - Both 32-bit and 64-bit systems supported
  - Requires 32-bit versions of oxipng/pngquant for x86 systems

**Minimum Hardware:**
- Processor: 1 GHz dual-core CPU
- RAM: 2 GB (4 GB recommended)
- Disk Space: 100 MB free space

**Dependencies:**
- Microsoft Visual C++ Redistributable 2015+
- Python 3.8+ (32-bit or 64-bit)

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
1. Select Input Folder
Choose directory with images to process
2. Configure Settings


![image](https://github.com/user-attachments/assets/8d982866-e248-490c-8baa-7d42465b0b9b)


3. Select file formats (PNG/JPG)
4. Set compression level (1-100)
5. Choose resizing options
6. Configure alpha channel handling
7. Start Processing
Optimized images save to jackpressed/ subdirectory

Technical Highlights 🧠

```bash
# Smart quality remapping for JPEG
def _calculate_quality(compression_level: int) -> int:
    normalized = (compression_level - 1) / 99
    return MIN_QUALITY + int(normalized**2 * (MAX_QUALITY - MIN_QUALITY))
```
License 📄
MIT License - See LICENSE for details.

Developed with ❤️ by Pavel Zosim
https://www.pavelzosim.com






    
