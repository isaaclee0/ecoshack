#!/usr/bin/env python3
"""
Image Downloader for Eco Shack Project
Parses images.xml file and downloads all images from WordPress export
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, unquote
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image, ImageOps
import argparse

class ImageOptimizer:
    """Handles web optimization of images"""
    
    # Standard web image sizes
    SIZES = {
        'thumbnail': 300,
        'medium': 800,
        'large': 1200,
        'xlarge': 1920
    }
    
    def __init__(self, quality=85, progressive=True):
        self.quality = quality
        self.progressive = progressive
    
    def optimize_image(self, input_path, output_dir, create_variants=True):
        """Optimize a single image for web use"""
        try:
            input_path = Path(input_path)
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
            
            # Open and process image
            with Image.open(input_path) as img:
                # Convert to RGB if necessary (handles RGBA, P mode, etc.)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Auto-orient based on EXIF data
                img = ImageOps.exif_transpose(img)
                
                original_size = img.size
                base_name = input_path.stem
                
                results = []
                
                if create_variants:
                    # Create multiple size variants
                    for size_name, max_dimension in self.SIZES.items():
                        variant_img = self._resize_image(img, max_dimension)
                        variant_path = output_dir / f"{base_name}_{size_name}.jpg"
                        
                        # Save optimized variant
                        variant_img.save(
                            variant_path,
                            'JPEG',
                            quality=self.quality,
                            progressive=self.progressive,
                            optimize=True
                        )
                        
                        results.append({
                            'size': size_name,
                            'path': variant_path,
                            'dimensions': variant_img.size,
                            'file_size': variant_path.stat().st_size
                        })
                else:
                    # Just optimize the original size
                    optimized_path = output_dir / f"{base_name}_optimized.jpg"
                    img.save(
                        optimized_path,
                        'JPEG',
                        quality=self.quality,
                        progressive=self.progressive,
                        optimize=True
                    )
                    
                    results.append({
                        'size': 'optimized',
                        'path': optimized_path,
                        'dimensions': img.size,
                        'file_size': optimized_path.stat().st_size
                    })
                
                return {
                    'success': True,
                    'original_size': original_size,
                    'original_file_size': input_path.stat().st_size,
                    'variants': results
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _resize_image(self, img, max_dimension):
        """Resize image maintaining aspect ratio"""
        width, height = img.size
        
        # If image is smaller than max_dimension, don't upscale
        if max(width, height) <= max_dimension:
            return img.copy()
        
        # Calculate new dimensions
        if width > height:
            new_width = max_dimension
            new_height = int((height * max_dimension) / width)
        else:
            new_height = max_dimension
            new_width = int((width * max_dimension) / height)
        
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

class ImageDownloader:
    def __init__(self, xml_file="images.xml", download_dir="downloaded_images"):
        self.xml_file = xml_file
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.session = self._create_session()
        self.downloaded_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.optimizer = ImageOptimizer()
        
    def _create_session(self):
        """Create a requests session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        return session
    
    def extract_image_urls(self):
        """Extract all image URLs from the XML file"""
        print(f"Parsing {self.xml_file}...")
        
        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            return []
        except FileNotFoundError:
            print(f"Error: {self.xml_file} not found!")
            return []
        
        # Find all wp:attachment_url elements
        urls = []
        namespaces = {'wp': 'http://wordpress.org/export/1.2/'}
        
        for attachment_url in root.findall('.//wp:attachment_url', namespaces):
            url = attachment_url.text
            if url and self._is_image_url(url):
                urls.append(url)
        
        # Also check for URLs in CDATA sections and guid elements
        xml_content = open(self.xml_file, 'r', encoding='utf-8').read()
        
        # Extract URLs from CDATA sections and other places
        url_pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|webp|svg)(?:-\w+)?(?:\?[^\s<>"]*)?'
        additional_urls = re.findall(url_pattern, xml_content, re.IGNORECASE)
        
        # Combine and deduplicate
        all_urls = list(set(urls + additional_urls))
        
        print(f"Found {len(all_urls)} unique image URLs")
        return all_urls
    
    def _is_image_url(self, url):
        """Check if URL points to an image file"""
        if not url:
            return False
        
        # Remove query parameters for extension check
        clean_url = url.split('?')[0]
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')
        return any(clean_url.lower().endswith(ext) for ext in image_extensions)
    
    def _get_filename_from_url(self, url):
        """Extract filename from URL"""
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # Decode URL encoding
        filename = unquote(filename)
        
        # If no filename or extension, generate one
        if not filename or '.' not in filename:
            # Use the last part of the path or generate from URL
            path_parts = [p for p in parsed_url.path.split('/') if p]
            if path_parts:
                filename = path_parts[-1]
            else:
                filename = f"image_{hash(url) % 10000}.jpg"
        
        # Ensure we have a valid filename
        if not any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
            filename += '.jpg'
        
        return filename
    
    def download_image(self, url):
        """Download a single image"""
        try:
            filename = self._get_filename_from_url(url)
            filepath = self.download_dir / filename
            
            # Skip if file already exists
            if filepath.exists():
                print(f"⏭️  Skipping {filename} (already exists)")
                self.skipped_count += 1
                return True
            
            print(f"📥 Downloading {filename}...")
            
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check if it's actually an image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                print(f"⚠️  Warning: {url} doesn't appear to be an image (content-type: {content_type})")
            
            # Write file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = filepath.stat().st_size
            print(f"✅ Downloaded {filename} ({file_size:,} bytes)")
            self.downloaded_count += 1
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to download {url}: {e}")
            self.failed_count += 1
            return False
        except Exception as e:
            print(f"❌ Unexpected error downloading {url}: {e}")
            self.failed_count += 1
            return False
    
    def download_all_images(self):
        """Download all images from the XML file"""
        urls = self.extract_image_urls()
        
        if not urls:
            print("No image URLs found in the XML file.")
            return
        
        print(f"\n🚀 Starting download of {len(urls)} images...")
        print(f"📁 Download directory: {self.download_dir.absolute()}")
        print("-" * 60)
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            self.download_image(url)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 DOWNLOAD SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully downloaded: {self.downloaded_count}")
        print(f"⏭️  Skipped (already exists): {self.skipped_count}")
        print(f"❌ Failed downloads: {self.failed_count}")
        print(f"📁 Total files in directory: {len(list(self.download_dir.glob('*')))}")
        print(f"📂 Download directory: {self.download_dir.absolute()}")
    
    def optimize_downloaded_images(self, create_variants=True, quality=85):
        """Optimize all downloaded images for web use"""
        optimized_dir = self.download_dir.parent / "optimized_images"
        optimized_dir.mkdir(exist_ok=True)
        
        # Get all image files
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
        image_files = []
        for ext in image_extensions:
            image_files.extend(self.download_dir.glob(f'*{ext}'))
            image_files.extend(self.download_dir.glob(f'*{ext.upper()}'))
        
        if not image_files:
            print("❌ No images found to optimize!")
            return
        
        print(f"\n🎨 Starting optimization of {len(image_files)} images...")
        print(f"📁 Output directory: {optimized_dir.absolute()}")
        print(f"⚙️  Quality: {quality}%, Variants: {'Yes' if create_variants else 'No'}")
        print("-" * 60)
        
        optimizer = ImageOptimizer(quality=quality)
        optimized_count = 0
        failed_count = 0
        total_original_size = 0
        total_optimized_size = 0
        
        for i, image_file in enumerate(image_files, 1):
            print(f"\n[{i}/{len(image_files)}] Optimizing: {image_file.name}")
            
            result = optimizer.optimize_image(image_file, optimized_dir, create_variants)
            
            if result['success']:
                optimized_count += 1
                original_size = result['original_file_size']
                total_original_size += original_size
                
                print(f"✅ Original: {original_size:,} bytes ({result['original_size'][0]}x{result['original_size'][1]})")
                
                for variant in result['variants']:
                    variant_size = variant['file_size']
                    total_optimized_size += variant_size
                    compression_ratio = (1 - variant_size / original_size) * 100
                    
                    print(f"   📐 {variant['size']}: {variant_size:,} bytes "
                          f"({variant['dimensions'][0]}x{variant['dimensions'][1]}) "
                          f"- {compression_ratio:.1f}% smaller")
            else:
                failed_count += 1
                print(f"❌ Failed: {result['error']}")
        
        # Summary
        total_compression = (1 - total_optimized_size / total_original_size) * 100 if total_original_size > 0 else 0
        
        print("\n" + "=" * 60)
        print("🎨 OPTIMIZATION SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully optimized: {optimized_count}")
        print(f"❌ Failed optimizations: {failed_count}")
        print(f"📊 Original total size: {total_original_size:,} bytes ({total_original_size/1024/1024:.1f} MB)")
        print(f"📊 Optimized total size: {total_optimized_size:,} bytes ({total_optimized_size/1024/1024:.1f} MB)")
        print(f"💾 Total space saved: {total_original_size - total_optimized_size:,} bytes ({total_compression:.1f}%)")
        print(f"📂 Optimized images directory: {optimized_dir.absolute()}")
        
        if create_variants:
            variant_counts = {}
            for variant_name in ImageOptimizer.SIZES.keys():
                count = len(list(optimized_dir.glob(f'*_{variant_name}.jpg')))
                variant_counts[variant_name] = count
            
            print(f"\n📐 Size variants created:")
            for variant_name, count in variant_counts.items():
                print(f"   {variant_name}: {count} images")
    
    def create_image_manifest(self):
        """Create a JSON manifest of all optimized images"""
        import json
        
        optimized_dir = self.download_dir.parent / "optimized_images"
        manifest_file = optimized_dir / "image_manifest.json"
        
        if not optimized_dir.exists():
            print("❌ No optimized images directory found. Run optimization first.")
            return
        
        manifest = {
            "generated_at": str(Path().cwd()),
            "total_images": 0,
            "images": {}
        }
        
        # Group images by base name
        image_files = list(optimized_dir.glob('*.jpg'))
        base_names = set()
        
        for img_file in image_files:
            # Extract base name (remove size suffix)
            name_parts = img_file.stem.split('_')
            if len(name_parts) > 1 and name_parts[-1] in ImageOptimizer.SIZES:
                base_name = '_'.join(name_parts[:-1])
            else:
                base_name = img_file.stem
            base_names.add(base_name)
        
        for base_name in sorted(base_names):
            variants = {}
            for size_name in ImageOptimizer.SIZES.keys():
                variant_file = optimized_dir / f"{base_name}_{size_name}.jpg"
                if variant_file.exists():
                    stat = variant_file.stat()
                    with Image.open(variant_file) as img:
                        variants[size_name] = {
                            "filename": variant_file.name,
                            "width": img.width,
                            "height": img.height,
                            "file_size": stat.st_size,
                            "path": str(variant_file.relative_to(optimized_dir))
                        }
            
            if variants:
                manifest["images"][base_name] = variants
                manifest["total_images"] += 1
        
        # Save manifest
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"📋 Image manifest created: {manifest_file}")
        print(f"📊 Catalogued {manifest['total_images']} images with {sum(len(variants) for variants in manifest['images'].values())} total variants")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Eco Shack Image Downloader and Optimizer')
    parser.add_argument('--download', action='store_true', help='Download images from XML file')
    parser.add_argument('--optimize', action='store_true', help='Optimize downloaded images for web')
    parser.add_argument('--quality', type=int, default=85, help='JPEG quality (1-100, default: 85)')
    parser.add_argument('--no-variants', action='store_true', help='Skip creating size variants')
    parser.add_argument('--manifest', action='store_true', help='Create image manifest JSON file')
    parser.add_argument('--all', action='store_true', help='Download, optimize, and create manifest')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help and default behavior
    if not any([args.download, args.optimize, args.manifest, args.all]):
        print("🖼️  Eco Shack Image Downloader and Optimizer")
        print("=" * 50)
        print("Usage examples:")
        print("  python download_images.py --download          # Download images only")
        print("  python download_images.py --optimize          # Optimize existing images")
        print("  python download_images.py --all               # Download + optimize + manifest")
        print("  python download_images.py --optimize --quality 90  # High quality optimization")
        print("\nRunning download by default...")
        args.download = True
    
    # Check if we're in the right directory
    if not os.path.exists("images.xml") and (args.download or args.all):
        print("❌ Error: images.xml not found in current directory!")
        print("Please run this script from the imagestock directory.")
        sys.exit(1)
    
    downloader = ImageDownloader()
    
    # Execute requested operations
    if args.all:
        print("🚀 Running complete workflow: Download → Optimize → Manifest")
        print("=" * 60)
        
        # Download
        downloader.download_all_images()
        
        # Optimize
        create_variants = not args.no_variants
        downloader.optimize_downloaded_images(create_variants=create_variants, quality=args.quality)
        
        # Create manifest
        downloader.create_image_manifest()
        
    else:
        if args.download:
            downloader.download_all_images()
        
        if args.optimize:
            create_variants = not args.no_variants
            downloader.optimize_downloaded_images(create_variants=create_variants, quality=args.quality)
        
        if args.manifest:
            downloader.create_image_manifest()

if __name__ == "__main__":
    main()