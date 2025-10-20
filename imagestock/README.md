# EcoShack Image Stock

This directory contains all images downloaded from the WordPress export file.

## Download Summary

- **Total Images Downloaded**: 85 JPG files
- **Total Size**: 64MB
- **Source**: `ecoshack.WordPress.2025-09-26.xml`
- **Format**: All images optimized and converted to JPEG format
- **Quality**: 85% JPEG compression with optimization
- **Max Resolution**: 2000px on longest side

## Script Features

The `download_images.py` script includes:

- **XML Parsing**: Extracts image URLs from WordPress export XML
- **Image Optimization**: 
  - Converts all formats to optimized JPEG
  - Resizes large images (max 2000px)
  - 85% quality compression
  - Removes transparency (white background)
- **Error Handling**: Graceful handling of failed downloads
- **Duplicate Prevention**: Skips already downloaded files
- **Safe Filenames**: Sanitizes filenames for filesystem compatibility

## Usage

To run the script again:

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Run the download script
python download_images.py
```

## File Structure

- `download_images.py` - Main download script
- `requirements.txt` - Python dependencies
- `venv/` - Python virtual environment
- `ecoshack.WordPress.2025-09-26.xml` - Source WordPress export
- `*.jpg` - Downloaded and optimized images

## Image Optimization Details

All images have been processed for web optimization:
- **Format**: JPEG (from various source formats including PNG)
- **Quality**: 85% (good balance of quality vs file size)
- **Size**: Maximum 2000px on longest dimension
- **Transparency**: Converted to white background
- **Compression**: Optimized for web delivery