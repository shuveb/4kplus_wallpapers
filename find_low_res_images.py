#!/usr/bin/env python3
"""
Script to find and optionally delete images below 4K resolution.
Searches recursively from the current directory.
"""

import os
import sys
from pathlib import Path
from PIL import Image
from collections import defaultdict
import argparse
import shutil

# 4K resolution threshold (3840x2160)
MIN_4K_WIDTH = 3840
MIN_4K_HEIGHT = 2160

# Supported image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.svg', '.ico'}

def is_image_file(filepath):
    """Check if a file is an image based on extension."""
    return filepath.suffix.lower() in IMAGE_EXTENSIONS

def get_image_resolution(filepath):
    """Get the resolution of an image file."""
    try:
        with Image.open(filepath) as img:
            return img.size  # Returns (width, height)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def is_below_4k(width, height):
    """Check if resolution is below 4K standard."""
    return width < MIN_4K_WIDTH or height < MIN_4K_HEIGHT

def format_resolution(width, height):
    """Format resolution for display."""
    return f"{width}x{height}"

def find_low_res_images(directory="."):
    """Find all images below 4K resolution in directory and subdirectories."""
    directory = Path(directory)
    low_res_images = []
    all_images = []
    resolution_stats = defaultdict(int)
    
    print(f"Scanning for images in: {directory.absolute()}")
    print("Finding image files...", end='', flush=True)
    
    # First, collect all image files
    image_files = []
    for filepath in directory.rglob("*"):
        if filepath.is_file() and is_image_file(filepath):
            image_files.append(filepath)
    
    print(f" Found {len(image_files)} images")
    print("Analyzing resolutions...", flush=True)
    
    # Process images with progress indicator
    for i, filepath in enumerate(image_files, 1):
        if i % 100 == 0:
            print(f"  Processing: {i}/{len(image_files)} ({i*100//len(image_files)}%)", end='\r', flush=True)
        
        resolution = get_image_resolution(filepath)
        if resolution:
            width, height = resolution
            res_key = format_resolution(width, height)
            resolution_stats[res_key] += 1
            
            image_info = {
                'path': filepath,
                'width': width,
                'height': height,
                'size': filepath.stat().st_size
            }
            
            all_images.append(image_info)
            
            if is_below_4k(width, height):
                low_res_images.append(image_info)
    
    print(f"  Processing: {len(image_files)}/{len(image_files)} (100%)    ")  # Clear the line
    print()
    
    return low_res_images, all_images, resolution_stats

def display_results(low_res_images, all_images, resolution_stats):
    """Display the results of the scan."""
    print("=" * 60)
    print("SCAN RESULTS")
    print("=" * 60)
    
    print(f"\nTotal images found: {len(all_images)}")
    print(f"Images below 4K resolution: {len(low_res_images)}")
    print(f"Images at or above 4K resolution: {len(all_images) - len(low_res_images)}")
    
    if low_res_images:
        print(f"\n{'─' * 60}")
        print("LOW RESOLUTION IMAGES (Below 4K)")
        print(f"{'─' * 60}")
        
        # Sort by resolution for better readability
        low_res_images.sort(key=lambda x: (x['width'] * x['height']))
        
        # Show first 50 images if there are many
        display_count = min(50, len(low_res_images))
        
        for i, img in enumerate(low_res_images[:display_count], 1):
            size_mb = img['size'] / (1024 * 1024)
            try:
                rel_path = img['path'].relative_to(Path.cwd())
            except ValueError:
                # If relative path fails, just use the absolute path
                rel_path = img['path']
            print(f"{i:4d}. {format_resolution(img['width'], img['height']):12s} "
                  f"({size_mb:6.2f} MB) - {rel_path}")
        
        if len(low_res_images) > display_count:
            print(f"\n  ... and {len(low_res_images) - display_count} more low-resolution images")
    
    print(f"\n{'─' * 60}")
    print("RESOLUTION STATISTICS (Top 10)")
    print(f"{'─' * 60}")
    
    # Sort resolutions by count
    sorted_stats = sorted(resolution_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    for resolution, count in sorted_stats:
        print(f"  {resolution:12s}: {count:4d} image(s)")
    
    if len(resolution_stats) > 10:
        print(f"  ... and {len(resolution_stats) - 10} more unique resolutions")

def delete_images(images):
    """Delete the specified images."""
    deleted_count = 0
    failed_count = 0
    total_size_freed = 0
    deleted_images = []
    
    print(f"\nDeleting {len(images)} images...")
    
    for img in images:
        try:
            size = img['size']
            img['path'].unlink()
            deleted_count += 1
            total_size_freed += size
            deleted_images.append(img)
            try:
                rel_path = img['path'].relative_to(Path.cwd())
            except ValueError:
                rel_path = img['path']
            print(f"  ✓ Deleted: {rel_path}")
        except Exception as e:
            failed_count += 1
            try:
                rel_path = img['path'].relative_to(Path.cwd())
            except ValueError:
                rel_path = img['path']
            print(f"  ✗ Failed to delete {rel_path}: {e}")
    
    print(f"\n{'─' * 60}")
    print(f"Deletion complete:")
    print(f"  - Successfully deleted: {deleted_count} images")
    if failed_count > 0:
        print(f"  - Failed to delete: {failed_count} images")
    print(f"  - Space freed: {total_size_freed / (1024 * 1024):.2f} MB")
    
    return deleted_images

def move_high_res_images(high_res_images, source_dir):
    """Move high-resolution images to a specified directory."""
    print(f"\n{'=' * 60}")
    print("MOVE HIGH-RESOLUTION IMAGES")
    print(f"{'=' * 60}")
    
    print(f"\nYou have {len(high_res_images)} high-resolution images remaining.")
    print("Would you like to move them to a different directory?")
    
    response = input("\nMove high-resolution images? [y/N]: ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("Move operation cancelled.")
        return
    
    # Get destination directory
    while True:
        dest_dir = input("\nEnter destination directory path: ").strip()
        if not dest_dir:
            print("Move operation cancelled.")
            return
        
        dest_path = Path(dest_dir).expanduser().absolute()
        
        # Create directory if it doesn't exist
        if not dest_path.exists():
            create = input(f"\nDirectory '{dest_path}' does not exist. Create it? [y/N]: ").strip().lower()
            if create in ['y', 'yes']:
                try:
                    dest_path.mkdir(parents=True, exist_ok=True)
                    print(f"✓ Created directory: {dest_path}")
                    break
                except Exception as e:
                    print(f"✗ Failed to create directory: {e}")
                    continue
            else:
                continue
        elif not dest_path.is_dir():
            print(f"Error: '{dest_path}' is not a directory.")
            continue
        else:
            break
    
    # Move images
    moved_count = 0
    failed_count = 0
    skipped_count = 0
    overwritten_count = 0
    overwrite_all = False
    
    print(f"\nMoving {len(high_res_images)} high-resolution images...")
    
    for i, img in enumerate(high_res_images, 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(high_res_images)} ({i*100//len(high_res_images)}%)")
        
        source_file = img['path']
        dest_file = dest_path / source_file.name
        
        try:
            # Check if destination file exists
            if dest_file.exists():
                # Check if it's the same file (by size and resolution)
                dest_resolution = get_image_resolution(dest_file)
                if dest_resolution and dest_resolution == (img['width'], img['height']) and \
                   dest_file.stat().st_size == img['size']:
                    # Same file, skip
                    skipped_count += 1
                    continue
                
                # Different file with same name - check if we should overwrite all
                if overwrite_all:
                    shutil.move(str(source_file), str(dest_file))
                    moved_count += 1
                    overwritten_count += 1
                else:
                    # Ask for confirmation
                    print(f"\n  Conflict: '{source_file.name}' already exists in destination")
                    print(f"    Source: {img['width']}x{img['height']} ({img['size'] / (1024*1024):.2f} MB)")
                    if dest_resolution:
                        dest_size = dest_file.stat().st_size
                        print(f"    Destination: {dest_resolution[0]}x{dest_resolution[1]} ({dest_size / (1024*1024):.2f} MB)")
                    
                    action = input("    Overwrite? [y/N/a (yes to all)]: ").strip().lower()
                    
                    if action == 'a':
                        # Set flag to overwrite all
                        overwrite_all = True
                        shutil.move(str(source_file), str(dest_file))
                        moved_count += 1
                        overwritten_count += 1
                    elif action in ['y', 'yes']:
                        shutil.move(str(source_file), str(dest_file))
                        moved_count += 1
                        overwritten_count += 1
                    else:
                        skipped_count += 1
            else:
                # No conflict, move the file
                shutil.move(str(source_file), str(dest_file))
                moved_count += 1
                
        except Exception as e:
            failed_count += 1
            print(f"  ✗ Failed to move {source_file.name}: {e}")
    
    # Clean up empty directories
    print("\nCleaning up empty directories...")
    cleaned_dirs = []
    for img in high_res_images:
        parent_dir = img['path'].parent
        if parent_dir != source_dir and parent_dir.exists():
            try:
                # Check if directory is empty
                if not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    if parent_dir not in cleaned_dirs:
                        cleaned_dirs.append(parent_dir)
            except:
                pass  # Directory not empty or can't be removed
    
    print(f"\n{'─' * 60}")
    print("Move operation complete:")
    print(f"  - Successfully moved: {moved_count} images")
    if overwritten_count > 0:
        print(f"  - Overwritten: {overwritten_count} images")
    if skipped_count > 0:
        print(f"  - Skipped (duplicates): {skipped_count} images")
    if failed_count > 0:
        print(f"  - Failed to move: {failed_count} images")
    if cleaned_dirs:
        print(f"  - Cleaned up {len(cleaned_dirs)} empty directories")
    print(f"  - Destination: {dest_path}")

def main():
    parser = argparse.ArgumentParser(description='Find and optionally delete images below 4K resolution')
    parser.add_argument('--auto-delete', '-y', action='store_true', 
                        help='Automatically delete low-res images without confirmation')
    parser.add_argument('--directory', '-d', default='.', 
                        help='Directory to scan (default: current directory)')
    
    args = parser.parse_args()
    
    # Find low resolution images
    low_res_images, all_images, resolution_stats = find_low_res_images(args.directory)
    
    # Display results
    display_results(low_res_images, all_images, resolution_stats)
    
    if not low_res_images:
        print("\n✓ No images below 4K resolution found!")
        return 0
    
    # Calculate total size
    total_size = sum(img['size'] for img in low_res_images)
    total_size_mb = total_size / (1024 * 1024)
    
    print(f"\n{'=' * 60}")
    print(f"Total size of low-resolution images: {total_size_mb:.2f} MB")
    print(f"{'=' * 60}")
    
    # Ask for confirmation unless auto-delete is enabled
    deleted_images = []
    if args.auto_delete:
        deleted_images = delete_images(low_res_images)
    else:
        print("\nWould you like to delete these low-resolution images?")
        print("WARNING: This action cannot be undone!")
        
        while True:
            response = input("\nDelete all low-resolution images? [y/N]: ").strip().lower()
            
            if response in ['y', 'yes']:
                deleted_images = delete_images(low_res_images)
                break
            elif response in ['n', 'no', '']:
                print("Deletion cancelled. No files were deleted.")
                break
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    # If images were deleted, offer to move high-res images
    if deleted_images:
        # Find remaining high-res images (those not deleted)
        deleted_paths = {img['path'] for img in deleted_images}
        high_res_images = [img for img in all_images if img['path'] not in deleted_paths]
        
        if high_res_images:
            move_high_res_images(high_res_images, Path(args.directory))
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)