"""
AutoCut Pro - Mini Tool
Super simple interface with one button per tool category

Features:
- Rotate Video (16:9 <-> 9:16)
- Crop (16:9, 9:16, 1:1, 4:3)
- Merge (All->1, Pairs 2->1)
- Speed Control
- Audio Extract
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
import os
import subprocess
import threading
from pathlib import Path
import sys
import json
import requests
import uuid
from datetime import datetime
import hashlib
import zipfile
import shutil
import platform
import urllib.request
import urllib.error
import time
from concurrent.futures import ThreadPoolExecutor
import io

# GPU detection and configuration
def detect_gpu_encoders(ffmpeg_path="ffmpeg"):
    """Detect available GPU encoders"""
    available_encoders = {
        'nvidia': None,
        'amd': None, 
        'intel': None,
        'cpu_only': True
    }
    
    try:
        
        # Get list of available encoders
        result = subprocess.run([ffmpeg_path, "-encoders"], capture_output=True, text=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
        if result.returncode == 0:
            encoders_output = result.stdout.lower()
            
            # Check for NVIDIA encoders
            if "h264_nvenc" in encoders_output:
                available_encoders['nvidia'] = 'h264_nvenc'
                available_encoders['cpu_only'] = False
                debug_log("NVIDIA GPU encoder detected: h264_nvenc")
            
            # Check for AMD encoders  
            if "h264_amf" in encoders_output:
                available_encoders['amd'] = 'h264_amf'
                available_encoders['cpu_only'] = False
                debug_log("AMD GPU encoder detected: h264_amf")
            
            # Check for Intel encoders
            if "h264_qsv" in encoders_output:
                available_encoders['intel'] = 'h264_qsv'
                available_encoders['cpu_only'] = False
                debug_log("Intel GPU encoder detected: h264_qsv")
                
    except Exception as e:
        debug_log(f"GPU detection error: {e}")
    
    return available_encoders

def get_optimal_encoding_settings(gpu_encoders):
    """Get optimal encoding settings based on available hardware"""
    settings = {
        'encoder': 'libx264',  # Default CPU encoder
        'preset': 'medium',
        'extra_args': [],
        'gpu_type': 'cpu'
    }
    
    # Priority: NVIDIA > AMD > Intel > CPU
    if gpu_encoders['nvidia']:
        settings.update({
            'encoder': 'h264_nvenc',
            'preset': 'p4',  # NVIDIA preset (p1=fastest, p7=slowest)
            'extra_args': ['-rc', 'vbr', '-cq', '23', '-b:v', '0'],
            'gpu_type': 'nvidia'
        })
        debug_log("Using NVIDIA GPU acceleration")
        
    elif gpu_encoders['amd']:
        settings.update({
            'encoder': 'h264_amf', 
            'preset': 'balanced',  # AMD preset
            'extra_args': ['-rc', 'vbr_peak', '-qp_i', '23', '-qp_p', '23'],
            'gpu_type': 'amd'
        })
        debug_log("Using AMD GPU acceleration")
        
    elif gpu_encoders['intel']:
        settings.update({
            'encoder': 'h264_qsv',
            'preset': 'medium',  # Intel preset  
            'extra_args': ['-global_quality', '23'],
            'gpu_type': 'intel'
        })
        debug_log("Using Intel GPU acceleration")
    else:
        debug_log("Using CPU encoding (no compatible GPU found)")
    
    return settings

# Cache GPU detection result
_gpu_encoders_cache = None
_encoding_settings_cache = None

def get_gpu_settings(ffmpeg_path="ffmpeg"):
    """Get cached GPU settings or detect if not cached"""
    global _gpu_encoders_cache, _encoding_settings_cache
    
    if _gpu_encoders_cache is None:
        _gpu_encoders_cache = detect_gpu_encoders(ffmpeg_path)
        _encoding_settings_cache = get_optimal_encoding_settings(_gpu_encoders_cache)
    
    return _encoding_settings_cache

# Suppress console window completely for compiled version
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    try:
        # Hide console window on Windows
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass
    
    # Redirect stdout and stderr to null
    try:
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    except:
        pass

# ---------------------------
# License Management System  
# ---------------------------

LICENSE_SERVER_BASE_URL = "https://license-server-pro.vercel.app/"
ACTIVATE_URL = f"{LICENSE_SERVER_BASE_URL}/api/license/activate"
REFRESH_URL = f"{LICENSE_SERVER_BASE_URL}/api/license/refresh"
PRODUCT_ID = "cutpro-mini"
HTTP_TIMEOUT = 15

def get_app_directory():
    """Get the application directory"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_machine_id():
    """Generate unique machine ID"""
    try:
        return hex(uuid.getnode())
    except Exception:
        return "generic-fallback-id"

def get_license_files():
    """Get license file paths"""
    app_dir = get_app_directory()
    token_file = os.path.join(app_dir, f"{PRODUCT_ID.replace('-', '_')}.license.token.json")
    code_file = os.path.join(app_dir, f"{PRODUCT_ID.replace('-', '_')}.license.code.txt")
    return token_file, code_file

def save_license_code(code):
    """Save license code to file"""
    try:
        _, code_file = get_license_files()
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code.strip())
    except Exception:
        pass

def load_license_code():
    """Load saved license code"""
    try:
        _, code_file = get_license_files()
        if os.path.exists(code_file):
            with open(code_file, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def save_token(token, expires_at=None, license_code=None, plan=None):
    """Save license token"""
    try:
        token_file, _ = get_license_files()
        data = {"token": token, "expiresAt": expires_at}
        if license_code:
            data["licenseCode"] = license_code
        if plan:
            data["plan"] = plan
        with open(token_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def load_token():
    """Load saved token"""
    try:
        token_file, _ = get_license_files()
        if os.path.exists(token_file):
            with open(token_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def activate_license(license_code, machine_id):
    """Activate license on server"""
    try:
        payload = {
            "licenseCode": license_code.strip(),
            "deviceId": machine_id.strip(), 
            "productId": PRODUCT_ID
        }
        r = requests.post(ACTIVATE_URL, json=payload, timeout=HTTP_TIMEOUT)
        if r.status_code != 200:
            try:
                msg = r.json().get("error", r.text)
            except Exception:
                msg = r.text
            return False, msg
        
        data = r.json()
        if not data.get("token"):
            return False, "Server returned no token"
            
        return True, data
    except Exception as e:
        return False, str(e)

def refresh_license(token):
    """Refresh license token"""
    try:
        r = requests.post(
            REFRESH_URL,
            json={"token": token},
            headers={"Content-Type": "application/json"},
            timeout=HTTP_TIMEOUT
        )
        if r.status_code != 200:
            try:
                msg = r.json().get("error", r.text)
            except Exception:
                msg = r.text
            return False, msg
            
        return True, r.json()
    except Exception as e:
        return False, str(e)

def is_token_expired(expires_at):
    """Check if token is expired"""
    if not expires_at:
        return False
    try:
        exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        now = datetime.now(exp_date.tzinfo)
        return now >= exp_date
    except Exception:
        return True

def get_remaining_days(expires_at):
    """Get remaining days from expiration date"""
    if not expires_at:
        return "Lifetime"
    try:
        exp_date = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        now = datetime.now(exp_date.tzinfo)
        days_left = (exp_date - now).days
        return max(0, days_left)
    except Exception:
        return 0

# ---------------------------
# FFmpeg Auto-Download System
# ---------------------------

def get_ffmpeg_folder():
    """Get the FFmpeg folder path"""
    app_dir = get_app_directory()
    return os.path.join(app_dir, "FFmpeg")

def get_ffmpeg_executable():
    """Get the FFmpeg executable path"""
    ffmpeg_folder = get_ffmpeg_folder()
    if platform.system() == "Windows":
        return os.path.join(ffmpeg_folder, "bin", "ffmpeg.exe")
    else:
        return os.path.join(ffmpeg_folder, "bin", "ffmpeg")

def is_ffmpeg_available():
    """Check if FFmpeg is available locally"""
    ffmpeg_path = get_ffmpeg_executable()
    return os.path.exists(ffmpeg_path) and os.path.isfile(ffmpeg_path)

def get_ffmpeg_download_urls():
    """Get list of fallback FFmpeg download URLs for the platform"""
    system = platform.system()
    if system == "Windows":
        return [
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",  # More reliable for compiled versions
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
            "https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip"
        ]
    elif system == "Darwin":  # macOS
        return [
            "https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip"
        ]
    else:  # Linux
        return [
            "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        ]

def get_ffmpeg_download_url():
    """Get the primary FFmpeg download URL for the platform"""
    urls = get_ffmpeg_download_urls()
    return urls[0] if urls else None

def find_aria2c():
    """Find aria2c executable for high-speed downloads"""
    # 1) Check if bundled with executable
    try:
        bundled = resource_path("aria2c.exe")
        if os.path.isfile(bundled):
            return bundled
    except:
        pass
    
    # 2) Check next to executable
    try:
        exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0])
        local = os.path.join(exe_dir, "aria2c.exe")
        if os.path.isfile(local):
            return local
    except:
        pass
    
    # 3) Check in PATH
    return shutil.which("aria2c")

def download_with_aria2(url, output_path, progress_callback=None):
    """Download using aria2c for maximum speed"""
    aria = find_aria2c()
    if not aria:
        return False
    
    if progress_callback:
        progress_callback("Using aria2c for ultra-fast download...")
    
    try:
        import subprocess
        
        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # aria2c command for maximum speed
        cmd = [
            aria,
            "-x", "16",                    # 16 connections per server
            "-s", "16",                    # split into 16 parts  
            "-k", "1M",                    # 1MB segment size
            "-j", "16",                    # max concurrent downloads
            "--max-download-limit=0",      # no speed limit
            "--disable-ipv6=false",        # enable IPv6
            "--check-certificate=false",   # ignore SSL certificates
            "--allow-overwrite=true",      # overwrite existing files
            "-o", os.path.basename(output_path),
            url,
        ]
        
        if progress_callback:
            progress_callback("Starting 16-connection aria2c download...")
        
        # Run aria2c
        result = subprocess.run(
            cmd, 
            cwd=os.path.dirname(output_path),
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            if progress_callback:
                if os.path.exists(output_path):
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    progress_callback(f"Ultra-fast download complete! {size_mb:.1f}MB via aria2c")
            return True
        else:
            if progress_callback:
                progress_callback("aria2c failed, falling back to requests...")
            return False
            
    except Exception as e:
        if progress_callback:
            progress_callback(f"aria2c error: {str(e)[:30]}... falling back...")
        return False

def download_with_requests(url, output_path, progress_callback=None):
    """Reliable requests-based download"""
    try:
        import requests
        
        if progress_callback:
            progress_callback("Using requests for reliable download...")
        
        session = requests.Session()
        session.verify = False  # Disable SSL verification
        
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        start_time = time.time()
        last_update = 0
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    current_time = time.time()
                    if current_time - last_update > 1.0:  # Update every second
                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            mb_downloaded = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            
                            elapsed = current_time - start_time
                            if elapsed > 1:
                                speed_mbps = (downloaded * 8) / (elapsed * 1000000)
                                progress_callback(f"Downloading {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) @ {speed_mbps:.1f}Mbps")
                            else:
                                progress_callback(f"Downloading {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB)")
                        last_update = current_time
        
        response.close()
        session.close()
        
        if progress_callback:
            total_mb = os.path.getsize(output_path) / (1024 * 1024)
            elapsed = time.time() - start_time
            avg_speed_mbps = (os.path.getsize(output_path) * 8) / (elapsed * 1000000) if elapsed > 0 else 0
            progress_callback(f"Download complete! {total_mb:.1f}MB in {elapsed:.1f}s @ {avg_speed_mbps:.1f}Mbps")
        
        return True
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"Requests download failed: {str(e)}")
        return False

def extract_bundled_ffmpeg(progress_callback=None):
    """Extract bundled FFmpeg from executable resources"""
    try:
        if progress_callback:
            progress_callback("Setting up FFmpeg from bundled resources...")
        
        # Get target FFmpeg folder
        ffmpeg_folder = get_ffmpeg_folder()
        os.makedirs(ffmpeg_folder, exist_ok=True)
        
        if progress_callback:
            progress_callback("Locating bundled FFmpeg...")
        
        # Get bundled FFmpeg path (from PyInstaller bundle)
        bundled_ffmpeg_path = None
        
        # Method 1: Try PyInstaller resource path
        try:
            bundled_ffmpeg_path = resource_path("FFmpeg")
            if progress_callback:
                progress_callback(f"Found FFmpeg bundle at: {bundled_ffmpeg_path[:50]}...")
        except Exception as e:
            if progress_callback:
                progress_callback(f"Resource path failed: {str(e)[:30]}")
        
        # Method 2: Try relative to executable
        if not bundled_ffmpeg_path or not os.path.exists(bundled_ffmpeg_path):
            try:
                base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
                bundled_ffmpeg_path = os.path.join(base_dir, "FFmpeg")
                if progress_callback:
                    progress_callback(f"Trying relative path: {bundled_ffmpeg_path[:50]}...")
            except:
                pass
        
        # Method 3: Try _MEIPASS directly
        if not bundled_ffmpeg_path or not os.path.exists(bundled_ffmpeg_path):
            try:
                if hasattr(sys, '_MEIPASS'):
                    bundled_ffmpeg_path = os.path.join(sys._MEIPASS, "FFmpeg")
                    if progress_callback:
                        progress_callback(f"Trying MEIPASS: {bundled_ffmpeg_path[:50]}...")
            except:
                pass
        
        if not bundled_ffmpeg_path or not os.path.exists(bundled_ffmpeg_path):
            raise Exception("Bundled FFmpeg not found in executable")
        
        if progress_callback:
            progress_callback("Found FFmpeg bundle - starting extraction...")
        
        # Check source bin folder
        source_bin_folder = os.path.join(bundled_ffmpeg_path, "bin")
        if not os.path.exists(source_bin_folder):
            raise Exception(f"FFmpeg bin folder not found at: {source_bin_folder}")
        
        # List files to copy
        ffmpeg_files = []
        try:
            ffmpeg_files = os.listdir(source_bin_folder)
            if progress_callback:
                progress_callback(f"Found {len(ffmpeg_files)} FFmpeg files to extract...")
        except Exception as e:
            raise Exception(f"Cannot list FFmpeg files: {str(e)}")
        
        # Prepare target folder
        target_bin_folder = os.path.join(ffmpeg_folder, "bin")
        
        # Remove existing bin folder if it exists
        if os.path.exists(target_bin_folder):
            if progress_callback:
                progress_callback("Removing old FFmpeg installation...")
            shutil.rmtree(target_bin_folder)
        
        # Create new bin folder
        os.makedirs(target_bin_folder, exist_ok=True)
        
        if progress_callback:
            progress_callback("Copying FFmpeg binaries (this may take a moment)...")
        
        # Copy files one by one with progress
        for i, filename in enumerate(ffmpeg_files):
            source_file = os.path.join(source_bin_folder, filename)
            target_file = os.path.join(target_bin_folder, filename)
            
            try:
                shutil.copy2(source_file, target_file)
                if progress_callback:
                    progress = int(((i + 1) / len(ffmpeg_files)) * 100)
                    progress_callback(f"Extracting {filename}... ({progress}%)")
            except Exception as e:
                raise Exception(f"Failed to copy {filename}: {str(e)}")
        
        # Verify extraction
        if progress_callback:
            progress_callback("Verifying extraction...")
        
        extracted_files = os.listdir(target_bin_folder)
        if len(extracted_files) != len(ffmpeg_files):
            raise Exception(f"Extraction incomplete: {len(extracted_files)}/{len(ffmpeg_files)} files")
        
        # Check if ffmpeg.exe exists and is executable
        ffmpeg_exe = os.path.join(target_bin_folder, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_exe):
            raise Exception("ffmpeg.exe not found after extraction")
        
        if progress_callback:
            progress_callback("FFmpeg extracted successfully!")
        
        return True
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"FFmpeg extraction failed: {str(e)}")
        return False

def download_with_ultra_speed(progress_callback=None):
    """Ultra-high speed download using multiple concurrent connections for 65+ Mbps"""
    try:
        if progress_callback:
            progress_callback("ULTRA SPEED: Preparing maximum bandwidth download...")
        
        import concurrent.futures
        import threading
        import time
        
        ffmpeg_folder = get_ffmpeg_folder()
        os.makedirs(ffmpeg_folder, exist_ok=True)
        filename = os.path.join(ffmpeg_folder, "ffmpeg_temp.zip")
        
        urls = get_ffmpeg_download_urls()
        
        # Ultra-high speed settings for 65+ Mbps connections
        MAX_CONNECTIONS = 32  # 32 parallel connections
        CHUNK_SIZE = 2 * 1024 * 1024  # 2MB chunks
        TIMEOUT = 30
        
        for url_index, url in enumerate(urls):
            try:
                if progress_callback:
                    progress_callback(f"ULTRA SPEED Server {url_index + 1}: Connecting...")
                
                # Get file size
                import urllib.request
                import urllib.error
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                try:
                    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                        total_size = int(response.headers.get('Content-Length', 0))
                        if total_size == 0:
                            continue
                except:
                    continue
                
                if progress_callback:
                    progress_callback(f"ULTRA SPEED: File size {total_size // (1024*1024)}MB - Starting {MAX_CONNECTIONS} connections...")
                
                # Calculate chunk ranges for parallel download
                chunk_size = max(CHUNK_SIZE, total_size // MAX_CONNECTIONS)
                ranges = []
                for i in range(0, total_size, chunk_size):
                    end = min(i + chunk_size - 1, total_size - 1)
                    ranges.append((i, end))
                
                # Pre-allocate file
                with open(filename, 'wb') as f:
                    f.seek(total_size - 1)
                    f.write(b'\0')
                
                # Download chunks concurrently
                downloaded_chunks = {}
                download_lock = threading.Lock()
                start_time = time.time()
                last_update = start_time
                
                def download_chunk(chunk_info):
                    start, end = chunk_info
                    chunk_req = urllib.request.Request(url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Range': f'bytes={start}-{end}'
                    })
                    
                    try:
                        with urllib.request.urlopen(chunk_req, timeout=TIMEOUT) as chunk_response:
                            chunk_data = chunk_response.read()
                            
                            with download_lock:
                                downloaded_chunks[start] = chunk_data
                                
                    except Exception as e:
                        debug_log(f"Chunk download error {start}-{end}: {e}")
                        return 0
                    
                    return len(chunk_data)
                
                # Use ThreadPoolExecutor for maximum concurrency
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONNECTIONS) as executor:
                    # Submit all chunk downloads
                    futures = {executor.submit(download_chunk, chunk_range): chunk_range for chunk_range in ranges}
                    
                    completed_size = 0
                    
                    # Process completed chunks
                    for future in concurrent.futures.as_completed(futures, timeout=300):
                        try:
                            chunk_size_downloaded = future.result()
                            completed_size += chunk_size_downloaded
                            
                            # Update progress
                            current_time = time.time()
                            if progress_callback and (current_time - last_update) > 0.3:
                                progress = int((completed_size / total_size) * 100)
                                mb_downloaded = completed_size / (1024 * 1024)
                                mb_total = total_size / (1024 * 1024)
                                elapsed = current_time - start_time
                                
                                if elapsed > 0.1:
                                    speed_mbps = (completed_size / (1024 * 1024)) / elapsed
                                    speed_mbits = speed_mbps * 8  # Convert MB/s to Mbps for display
                                    if speed_mbps >= 7:  # 7MB/s = 56Mbps (near max for 65Mbps connection)
                                        progress_callback(f"🚀 MAX SPEED {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) - {speed_mbps:.1f}MB/s ({speed_mbits:.0f}Mbps)")
                                    elif speed_mbps >= 5:  # 5MB/s = 40Mbps
                                        progress_callback(f"🚀 ULTRA FAST {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) - {speed_mbps:.1f}MB/s ({speed_mbits:.0f}Mbps)")
                                    elif speed_mbps >= 3:  # 3MB/s = 24Mbps
                                        progress_callback(f"🚀 FAST {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) - {speed_mbps:.1f}MB/s ({speed_mbits:.0f}Mbps)")
                                    else:
                                        progress_callback(f"⚡ DOWNLOADING {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) - {speed_mbps:.1f}MB/s ({speed_mbits:.0f}Mbps)")
                                
                                last_update = current_time
                                
                        except Exception as e:
                            debug_log(f"Future processing error: {e}")
                            continue
                
                # Write all chunks to file in correct order
                if progress_callback:
                    progress_callback("ULTRA SPEED: Assembling file...")
                
                with open(filename, 'r+b') as f:
                    for start_pos in sorted(downloaded_chunks.keys()):
                        f.seek(start_pos)
                        f.write(downloaded_chunks[start_pos])
                    f.flush()
                
                # Verify file size
                actual_size = os.path.getsize(filename)
                if actual_size == total_size:
                    if progress_callback:
                        total_time = time.time() - start_time
                        avg_speed = (total_size / (1024 * 1024)) / total_time if total_time > 0 else 0
                        avg_speed_mbits = avg_speed * 8
                        progress_callback(f"✅ COMPLETE! {actual_size // (1024*1024)}MB in {total_time:.1f}s - Avg: {avg_speed:.1f}MB/s ({avg_speed_mbits:.0f}Mbps)")
                    
                    # Extract FFmpeg
                    if progress_callback:
                        progress_callback("Extracting FFmpeg...")
                    
                    import zipfile, shutil
                    with zipfile.ZipFile(filename, 'r') as zip_ref:
                        temp_extract = os.path.join(ffmpeg_folder, "temp")
                        zip_ref.extractall(temp_extract)
                        
                        extracted_folders = [f for f in os.listdir(temp_extract) 
                                           if os.path.isdir(os.path.join(temp_extract, f))]
                        if extracted_folders:
                            source_folder = os.path.join(temp_extract, extracted_folders[0])
                            bin_source = os.path.join(source_folder, "bin")
                            bin_target = os.path.join(ffmpeg_folder, "bin")
                            
                            if os.path.exists(bin_source):
                                if os.path.exists(bin_target):
                                    shutil.rmtree(bin_target)
                                shutil.move(bin_source, bin_target)
                    
                    # Cleanup
                    try:
                        os.remove(filename)
                        shutil.rmtree(os.path.join(ffmpeg_folder, "temp"))
                    except:
                        pass
                    
                    return True
                
            except Exception as e:
                debug_log(f"Ultra speed download error for URL {url}: {e}")
                continue
        
        # All URLs failed, fallback
        debug_log("All ultra speed attempts failed, falling back")
        return download_with_requests_simple(progress_callback)
        
    except Exception as e:
        debug_log(f"Ultra speed setup error: {e}")
        return download_with_requests_simple(progress_callback)

def get_aria2_path():
    """Get path to aria2 executable with enhanced detection"""
    debug_log("Searching for aria2c executable...")
    
    # Method 1: Check bundled with compiled application
    bundled_path = resource_path("aria2c.exe" if sys.platform.startswith('win') else "aria2c")
    debug_log(f"Checking bundled path: {bundled_path}")
    if os.path.exists(bundled_path):
        debug_log(f"Found bundled aria2c at: {bundled_path}")
        return bundled_path
    
    # Method 2: Check current directory (for development)
    local_path = "aria2c.exe" if sys.platform.startswith('win') else "aria2c"
    debug_log(f"Checking local path: {local_path}")
    if os.path.exists(local_path):
        debug_log(f"Found local aria2c at: {local_path}")
        return os.path.abspath(local_path)
    
    # Method 3: Check system PATH
    try:
        debug_log("Checking system PATH for aria2c...")
        result = subprocess.run(['aria2c', '--version'], capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
        if result.returncode == 0:
            debug_log("Found aria2c in system PATH")
            return 'aria2c'
    except Exception as e:
        debug_log(f"System PATH check failed: {e}")
    
    # Method 4: Check common installation locations
    common_paths = [
        "C:\\Program Files\\aria2\\aria2c.exe",
        "C:\\Program Files (x86)\\aria2\\aria2c.exe",
        "/usr/bin/aria2c",
        "/usr/local/bin/aria2c"
    ]
    
    for path in common_paths:
        debug_log(f"Checking common path: {path}")
        if os.path.exists(path):
            debug_log(f"Found aria2c at common location: {path}")
            return path
    
    debug_log("aria2c not found anywhere!")
    return None

def download_with_aria2(progress_callback=None):
    """Ultra-fast download using aria2 with maximum parallel connections"""
    try:
        if progress_callback:
            progress_callback("Setting up ultra-fast download...")
        
        # Check if aria2 is available
        aria2_path = get_aria2_path()
        if not aria2_path:
            debug_log("aria2 not found, falling back to standard download")
            return download_with_requests_simple(progress_callback)
        
        ffmpeg_folder = get_ffmpeg_folder()
        os.makedirs(ffmpeg_folder, exist_ok=True)
        filename = os.path.join(ffmpeg_folder, "ffmpeg_temp.zip")
        
        urls = get_ffmpeg_download_urls()
        
        for i, url in enumerate(urls):
            try:
                if progress_callback:
                    progress_callback(f"🚀 ULTRA Server {i+1}: Preparing max speed...")
                
                # aria2 command with OPTIMIZED MAXIMUM BANDWIDTH settings
                aria2_cmd = [
                    aria2_path,
                    # Optimized connection settings for real-world maximum speed
                    "--max-connection-per-server=16",    # 16 connections (optimal for most servers)
                    "--max-concurrent-downloads=1", 
                    "--split=16",                        # Split into 16 segments for reliability
                    "--min-split-size=1M",               # 1MB minimum for efficiency
                    
                    # Aggressive bandwidth settings
                    "--max-download-limit=0",            # Remove all speed limits
                    "--max-overall-download-limit=0",    # No overall limit
                    "--max-upload-limit=0",              # No upload limit
                    
                    # Optimized buffer settings for 70MB+ connections
                    "--piece-length=1M",                 # 1MB pieces
                    "--disk-cache=64M",                  # 64MB disk cache for speed
                    "--max-tries=3",                     # Quick failure for speed
                    "--retry-wait=2",                    # 2-second retry
                    
                    # Connection optimization for maximum throughput
                    "--timeout=120",                     # 2-minute timeout for large files
                    "--connect-timeout=60",              # 1-minute connect timeout
                    "--bt-max-peers=0",                  # Disable P2P overhead
                    
                    # File system optimization
                    "--file-allocation=prealloc",        # Pre-allocate for maximum speed
                    "--check-integrity=false",           # Skip integrity for speed
                    "--continue=true",                   # Resume capability
                    "--auto-file-renaming=false",        # Don't rename files
                    "--conditional-get=false",           # Skip conditional checks
                    
                    # HTTP/HTTPS optimization for maximum speed
                    "--enable-http-pipelining=true",     # HTTP pipelining
                    "--enable-http-keep-alive=true",     # Keep connections alive
                    "--http-accept-gzip=true",           # Accept compression
                    "--http-no-cache=true",              # Skip cache checks for speed
                    "--user-agent=aria2/1.37.0",        # Simple user agent
                    
                    # Advanced speed optimizations
                    "--optimize-concurrent-downloads=true", # Optimize concurrent downloads
                    "--uri-selector=adaptive",           # Adaptive URI selection
                    "--stream-piece-selector=geom",      # Geometric piece selection
                    
                    # Progress and logging
                    "--summary-interval=1",              # Progress every second
                    "--download-result=hide",            # Hide result for speed
                    "--console-log-level=error",         # Only errors
                    "--log-level=error",                 # Minimal logging
                    
                    # Output settings
                    "--dir=" + ffmpeg_folder,            # Output directory
                    "--out=ffmpeg_temp.zip",             # Output filename
                    "--allow-overwrite=true",            # Allow overwrite
                    "--remove-control-file=true",        # Clean up control files
                    
                    url
                ]
                
                debug_log("ULTRA MAX: Using aria2 with 16 optimized connections for maximum bandwidth")
                if progress_callback:
                    progress_callback("🚀 ULTRA MAX: aria2 detected - preparing maximum bandwidth download...")
                
                if progress_callback:
                    progress_callback("🚀 ULTRA Starting maximum speed download...")
                
                # Start aria2 process
                import time
                process = subprocess.Popen(
                    aria2_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0
                )
                
                # Monitor progress
                start_time = time.time()
                last_update = start_time
                
                while process.poll() is None:
                    time.sleep(0.2)  # Check every 200ms
                    
                    # Check if file exists and get size for progress
                    if os.path.exists(filename):
                        try:
                            current_size = os.path.getsize(filename)
                            current_time = time.time()
                            
                            if progress_callback and (current_time - last_update) > 0.5:
                                elapsed = current_time - start_time
                                if elapsed > 0.1:
                                    mb_downloaded = current_size / (1024 * 1024)
                                    speed_mbps = mb_downloaded / elapsed
                                    
                                    if speed_mbps >= 200:
                                        progress_callback(f"🚀 ULTRA BEAST {mb_downloaded:.1f}MB - {speed_mbps:.0f}MB/s")
                                    elif speed_mbps >= 150:
                                        progress_callback(f"🚀 ULTRA MAX {mb_downloaded:.1f}MB - {speed_mbps:.0f}MB/s")
                                    elif speed_mbps >= 100:
                                        progress_callback(f"🚀 ULTRA FAST {mb_downloaded:.1f}MB - {speed_mbps:.0f}MB/s")
                                    elif speed_mbps >= 70:
                                        progress_callback(f"🚀 ULTRA {mb_downloaded:.1f}MB - {speed_mbps:.0f}MB/s")
                                    elif speed_mbps >= 50:
                                        progress_callback(f"⚡ FAST {mb_downloaded:.1f}MB - {speed_mbps:.0f}MB/s")
                                    else:
                                        progress_callback(f"📡 STANDARD {mb_downloaded:.1f}MB - {speed_mbps:.0f}MB/s")
                                
                                last_update = current_time
                        except:
                            pass
                
                # Check if download completed successfully
                return_code = process.wait()
                if return_code == 0 and os.path.exists(filename):
                    if progress_callback:
                        final_size = os.path.getsize(filename) / (1024 * 1024)
                        total_time = time.time() - start_time
                        avg_speed = final_size / total_time if total_time > 0 else 0
                        progress_callback(f"✅ ULTRA Complete! {final_size:.1f}MB in {total_time:.1f}s - Avg: {avg_speed:.0f}MB/s")
                    
                    # Extract FFmpeg using existing extraction code
                    if progress_callback:
                        progress_callback("Extracting FFmpeg...")
                    
                    import zipfile
                    with zipfile.ZipFile(filename, 'r') as zip_ref:
                        temp_extract = os.path.join(ffmpeg_folder, "temp")
                        zip_ref.extractall(temp_extract)
                        
                        extracted_folders = [f for f in os.listdir(temp_extract) 
                                           if os.path.isdir(os.path.join(temp_extract, f))]
                        if extracted_folders:
                            source_folder = os.path.join(temp_extract, extracted_folders[0])
                            bin_source = os.path.join(source_folder, "bin")
                            bin_target = os.path.join(ffmpeg_folder, "bin")
                            
                            if os.path.exists(bin_source):
                                if os.path.exists(bin_target):
                                    import shutil
                                    shutil.rmtree(bin_target)
                                shutil.move(bin_source, bin_target)
                    
                    # Cleanup
                    try:
                        os.remove(filename)
                        import shutil
                        shutil.rmtree(os.path.join(ffmpeg_folder, "temp"))
                    except:
                        pass
                    
                    return True
                else:
                    debug_log(f"aria2 download failed with return code: {return_code}")
                
            except Exception as e:
                debug_log(f"aria2 download error: {e}")
                continue
        
        # If all aria2 attempts failed, fallback
        debug_log("All aria2 attempts failed, falling back to standard download")
        return download_with_requests_simple(progress_callback)
        
    except Exception as e:
        debug_log(f"aria2 setup error: {e}")
        return download_with_requests_simple(progress_callback)

def download_with_requests_simple(progress_callback=None):
    """Simple urllib download that works reliably in compiled versions"""
    try:
        if progress_callback:
            progress_callback("Setting up download...")
        
        # Use urllib instead of requests for better PyInstaller compatibility
        import urllib.request
        import urllib.error
        import ssl
        
        # Create optimized SSL context for maximum speed
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            # Performance optimizations
            ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            ssl_context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3
            ssl_context.options |= ssl.OP_SINGLE_DH_USE | ssl.OP_SINGLE_ECDH_USE
        except:
            ssl_context = None
        
        ffmpeg_folder = get_ffmpeg_folder()
        os.makedirs(ffmpeg_folder, exist_ok=True)
        filename = os.path.join(ffmpeg_folder, "ffmpeg_temp.zip")
        
        urls = get_ffmpeg_download_urls()
        
        for i, url in enumerate(urls):
            try:
                if progress_callback:
                    progress_callback(f"Trying server {i+1}: {url.split('/')[2]}...")
                
                # Create request with headers for maximum speed
                request = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache'
                })
                
                if progress_callback:
                    progress_callback("Connecting...")
                
                # Open connection with optimized settings for maximum speed
                if ssl_context:
                    response = urllib.request.urlopen(request, context=ssl_context, timeout=30)
                else:
                    response = urllib.request.urlopen(request, timeout=30)
                
                # Set ultra-high socket buffer sizes for maximum and consistent throughput
                try:
                    import socket
                    sock = response.fp.raw._sock if hasattr(response.fp, 'raw') and hasattr(response.fp.raw, '_sock') else None
                    if sock:
                        # Ultra-large buffers for consistent 70MB+ speeds
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32 * 1024 * 1024)  # 32MB receive buffer
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 32 * 1024 * 1024)  # 32MB send buffer
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
                        try:
                            # Windows-specific optimizations for sustained speed
                            if hasattr(socket, 'SO_REUSEADDR'):
                                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                            # Additional optimizations for sustained throughput
                            if hasattr(socket, 'SO_KEEPALIVE'):
                                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                        except:
                            pass
                        debug_log("Ultra-high speed socket buffers configured: 32MB")
                except Exception as e:
                    debug_log(f"Socket optimization warning: {e}")
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                if progress_callback:
                    if total_size > 0:
                        mb_total = total_size / (1024 * 1024)
                        progress_callback(f"Downloading {mb_total:.1f}MB...")
                    else:
                        progress_callback("Starting download...")
                
                # Ultra-high speed download optimization for 50-80MB/s
                import tempfile
                import threading
                import queue
                
                # Create temporary file for writing
                with tempfile.NamedTemporaryFile(delete=False) as temp_f:
                    temp_filename = temp_f.name
                
                try:
                    # Ultra-stable high-speed download for consistent 50MB/s+
                    import time
                    
                    # Optimal settings for rock-solid 50MB/s+ speeds
                    optimal_chunk_size = 4 * 1024 * 1024  # 4MB chunks for stability
                    read_buffer_size = 64 * 1024 * 1024   # 64MB read buffer
                    
                    # Use memory-mapped approach for maximum speed stability
                    if total_size > 0:
                        # Pre-allocate entire file for zero-copy operations
                        with open(temp_filename, 'wb') as f:
                            f.seek(total_size - 1)
                            f.write(b'\0')
                        
                        # Memory map file for ultra-fast writing
                        import mmap
                        with open(temp_filename, 'r+b') as f:
                            with mmap.mmap(f.fileno(), 0) as mm:
                                # Ultra-aggressive read loop with memory mapping
                                downloaded = 0
                                start_time = time.time()
                                last_update = start_time
                                position = 0
                                
                                # Large buffer for consistent reads
                                buffer = bytearray(optimal_chunk_size)
                                
                                while downloaded < total_size:
                                    try:
                                        # Read large chunks consistently
                                        bytes_read = response.readinto(buffer)
                                        if not bytes_read:
                                            break
                                        
                                        # Direct memory copy (fastest possible)
                                        mm[position:position + bytes_read] = buffer[:bytes_read]
                                        position += bytes_read
                                        downloaded += bytes_read
                                        
                                        # Aggressive progress updates for speed monitoring
                                        current_time = time.time()
                                        if progress_callback and (current_time - last_update) > 0.15:
                                            progress = int((downloaded / total_size) * 100)
                                            mb_downloaded = downloaded / (1024 * 1024)
                                            mb_total = total_size / (1024 * 1024)
                                            elapsed = current_time - start_time
                                            if elapsed > 0.1:  # Avoid division by zero
                                                speed_mbps = (downloaded / (1024 * 1024)) / elapsed
                                                if speed_mbps >= 50:
                                                    progress_callback(f"🚀 ULTRA {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) - {speed_mbps:.1f}MB/s")
                                                elif speed_mbps >= 40:
                                                    progress_callback(f"⚡ FAST {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) - {speed_mbps:.1f}MB/s")
                                                else:
                                                    progress_callback(f"📡 BOOST {progress}% ({mb_downloaded:.1f}/{mb_total:.1f}MB) - {speed_mbps:.1f}MB/s")
                                            last_update = current_time
                                        
                                    except Exception as e:
                                        debug_log(f"Memory-mapped read error: {e}")
                                        # Continue without breaking to maintain speed
                                        continue
                                
                                # Force memory sync to disk
                                mm.flush()
                    
                    else:
                        # Fallback for unknown size - optimized streaming
                        debug_log("Using streaming download (unknown size)")
                        
                        # Ultra-large write buffer for consistent performance
                        write_buffer = bytearray()
                        buffer = bytearray(optimal_chunk_size)
                        downloaded = 0
                        start_time = time.time()
                        last_update = start_time
                        
                        # Collect data in large buffer, then write in big chunks
                        with open(temp_filename, 'wb', buffering=read_buffer_size) as f:
                            while True:
                                try:
                                    bytes_read = response.readinto(buffer)
                                    if not bytes_read:
                                        break
                                    
                                    # Accumulate in write buffer
                                    write_buffer.extend(buffer[:bytes_read])
                                    downloaded += bytes_read
                                    
                                    # Write buffer when it gets large (reduces I/O calls)
                                    if len(write_buffer) >= read_buffer_size:
                                        f.write(write_buffer)
                                        f.flush()
                                        write_buffer.clear()
                                    
                                    # Update progress
                                    current_time = time.time()
                                    if progress_callback and (current_time - last_update) > 0.2:
                                        mb_downloaded = downloaded / (1024 * 1024)
                                        elapsed = current_time - start_time
                                        if elapsed > 0.1:
                                            speed_mbps = mb_downloaded / elapsed
                                            if speed_mbps >= 50:
                                                progress_callback(f"🚀 ULTRA {mb_downloaded:.1f}MB - {speed_mbps:.1f}MB/s")
                                            else:
                                                progress_callback(f"📡 FAST {mb_downloaded:.1f}MB - {speed_mbps:.1f}MB/s")
                                        last_update = current_time
                                        
                                except Exception as e:
                                    debug_log(f"Streaming read error: {e}")
                                    continue
                            
                            # Write any remaining buffer
                            if write_buffer:
                                f.write(write_buffer)
                                f.flush()
                    
                    # Move temp file to final location
                    import shutil
                    shutil.move(temp_filename, filename)
                    debug_log(f"Download completed: {downloaded / (1024 * 1024):.1f}MB")
                    
                except Exception as e:
                    # Cleanup on error
                    try:
                        if os.path.exists(temp_filename):
                            os.remove(temp_filename)
                    except:
                        pass
                    raise e
                
                response.close()
                
                # Extract FFmpeg
                if progress_callback:
                    progress_callback("Extracting FFmpeg...")
                
                with zipfile.ZipFile(filename, 'r') as zip_ref:
                    temp_extract = os.path.join(ffmpeg_folder, "temp")
                    zip_ref.extractall(temp_extract)
                    
                    extracted_folders = [f for f in os.listdir(temp_extract) 
                                       if os.path.isdir(os.path.join(temp_extract, f))]
                    if extracted_folders:
                        source_folder = os.path.join(temp_extract, extracted_folders[0])
                        bin_source = os.path.join(source_folder, "bin")
                        bin_target = os.path.join(ffmpeg_folder, "bin")
                        
                        if os.path.exists(bin_source):
                            if os.path.exists(bin_target):
                                shutil.rmtree(bin_target)
                            shutil.move(bin_source, bin_target)
                    
                    shutil.rmtree(temp_extract, ignore_errors=True)
                
                os.remove(filename)
                
                if progress_callback:
                    progress_callback("FFmpeg installed successfully!")
                
                return True
                
            except Exception as e:
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except:
                        pass
                continue
        
        return False
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"Download failed: {str(e)}")
        return False

def ensure_ffmpeg_available(parent_window=None):
    """Ensure FFmpeg is available, download if needed"""
    if is_ffmpeg_available():
        return True
    
    # FFmpeg not found, need to download
    if parent_window:
        # Show download dialog
        dialog = FFmpegDownloadDialog(parent_window)
        return dialog.download_ffmpeg()
    else:
        # Silent download (fallback)
        return download_with_requests_simple()

# Function to get resource path (works for both dev and compiled)
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Function for debug logging (only prints in development)
def debug_log(message):
    """Log debug messages - only in development mode"""
    try:
        # Only enable debug in development, disable in compiled version
        if hasattr(sys, '_MEIPASS'):
            return  # Disable debug messages in compiled executable
    except:
        pass
    
    # Only print in development mode
    if not getattr(sys, 'frozen', False):
        print(f"[DEBUG] {message}")

# Apply appearance mode
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class CutPro:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Cut Pro - Mini Tool")
        self.root.geometry("700x610")
        self.root.minsize(700, 680)
        
        # Set application ID to separate from Python (Windows 7+)
        if sys.platform.startswith('win'):
            try:
                import ctypes
                # Set unique AppUserModelID to override Python grouping
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CutPro.VideoTool.1.0")
            except:
                pass
        
        # Set window icon (taskbar and title bar)
        self.icon_path = self.get_icon_path()
        
        # Set icon immediately
        self.set_main_window_icon()
        
        # Also set icon after window is fully initialized (for development mode)
        self.root.after(50, self.set_main_window_icon)
        self.root.after(100, self.set_main_window_icon)
        self.root.after(200, self.set_main_window_icon)
        self.root.after(500, self.set_main_window_icon)
        
        # Force taskbar icon update after window is shown
        self.root.after(1000, self.force_taskbar_icon)

        # Customize title bar color (Windows only)
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # Set title bar color to yellow (RGB: 255, 255, 0 -> 0xffff00)
            yellow_color = 0x0000ffff  # BGR format (Blue-Green-Red)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(yellow_color)), 4)
            # Enable custom title bar colors
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
        except:
            pass

        # Set custom background color with white border
        self.root.configure(fg_color="#34495e")
        
        # Create outer border frame
        outer_frame = ctk.CTkFrame(
            self.root,
            fg_color="#34495e",
            border_color="#ffffff",
            border_width=3,
            corner_radius=0
        )
        outer_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Center window on screen
        self.center_window()

        self.videos = []
        self.output_folder = ""
        self.license_valid = False
        self.remaining_days = 0
        self.permanent_status = None  # Store permanent status message

        # Create UI with license check
        self.create_ui(outer_frame)
        
        # Check FFmpeg availability after user sees the main tool
        self.root.after(5000, self.check_ffmpeg_setup)
        
        # Ensure taskbar icon is set after UI is created
        self.root.after(1000, self.ensure_taskbar_icon)
    
    def get_icon_path(self):
        """Get the correct icon path for both dev and compiled versions - enhanced"""
        debug_log("Searching for icon files...")
        
        # Method 1: Try compiled version paths first
        ico_path = resource_path("icon.ico")
        png_path = resource_path("icon.png")
        
        debug_log(f"Checking compiled ICO: {ico_path} - exists: {os.path.exists(ico_path)}")
        debug_log(f"Checking compiled PNG: {png_path} - exists: {os.path.exists(png_path)}")
        
        if os.path.exists(ico_path):
            debug_log(f"Found compiled icon.ico: {ico_path}")
            return ico_path
        elif os.path.exists(png_path):
            debug_log(f"Found compiled icon.png: {png_path}")
            return png_path
        
        # Method 2: Fallback to local paths for development
        if os.path.exists("icon.ico"):
            debug_log("Found local icon.ico")
            return "icon.ico"
        elif os.path.exists("icon.png"):
            debug_log("Found local icon.png") 
            return "icon.png"
        
        # Method 3: Check executable directory
        if hasattr(sys, '_MEIPASS'):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))
            
        exe_ico = os.path.join(exe_dir, "icon.ico")
        exe_png = os.path.join(exe_dir, "icon.png")
        
        debug_log(f"Checking exe dir ICO: {exe_ico} - exists: {os.path.exists(exe_ico)}")
        debug_log(f"Checking exe dir PNG: {exe_png} - exists: {os.path.exists(exe_png)}")
        
        if os.path.exists(exe_ico):
            debug_log(f"Found exe dir icon.ico: {exe_ico}")
            return exe_ico
        elif os.path.exists(exe_png):
            debug_log(f"Found exe dir icon.png: {exe_png}")
            return exe_png
        
        debug_log("No icon files found anywhere!")
        return None
    
    def set_main_window_icon(self):
        """Set main window icon for both window and taskbar - enhanced for compiled exe"""
        icon_set = False
        
        # Method 1: Try with the detected icon path
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                if self.icon_path.endswith('.ico'):
                    self.root.iconbitmap(self.icon_path)
                    self.root.wm_iconbitmap(self.icon_path)
                    icon_set = True
                    debug_log(f"Main window icon set via iconbitmap: {self.icon_path}")
                else:
                    # For PNG files, convert to PhotoImage
                    if not hasattr(self, '_main_icon_image'):
                        self._main_icon_image = tk.PhotoImage(file=self.icon_path)
                    self.root.iconphoto(True, self._main_icon_image)
                    self.root.wm_iconphoto(True, self._main_icon_image)
                    icon_set = True
                    debug_log(f"Main window icon set via iconphoto: {self.icon_path}")
            except Exception as e:
                debug_log(f"Method 1 icon setting failed: {e}")
        
        # Method 2: Try alternative paths for compiled executable
        if not icon_set:
            icon_attempts = [
                resource_path("icon.ico"),
                resource_path("icon.png"),
                os.path.join(os.path.dirname(sys.executable), "icon.ico"),
                os.path.join(os.path.dirname(sys.executable), "icon.png"),
                "icon.ico",
                "icon.png"
            ]
            
            for icon_path in icon_attempts:
                if os.path.exists(icon_path):
                    try:
                        if icon_path.endswith('.ico'):
                            self.root.iconbitmap(icon_path)
                            self.root.wm_iconbitmap(icon_path)
                            icon_set = True
                            debug_log(f"Main window icon set via alternative ICO: {icon_path}")
                            break
                        else:
                            temp_image = tk.PhotoImage(file=icon_path)
                            self.root.iconphoto(True, temp_image)
                            self.root.wm_iconphoto(True, temp_image)
                            # Keep reference to prevent garbage collection
                            self._main_icon_image = temp_image
                            icon_set = True
                            debug_log(f"Main window icon set via alternative PNG: {icon_path}")
                            break
                    except Exception as e:
                        debug_log(f"Alternative icon path failed {icon_path}: {e}")
                        continue
        
        # Method 3: Try Windows-specific icon setting for compiled exe
        if not icon_set and sys.platform.startswith('win'):
            try:
                import ctypes
                from ctypes import wintypes
                
                # Get window handle
                hwnd = self.root.winfo_id()
                if hwnd:
                    # Try to load icon from exe resources
                    hicon = ctypes.windll.user32.LoadIconW(0, 32512)  # IDI_APPLICATION
                    if hicon:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)  # WM_SETICON, ICON_LARGE
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)  # WM_SETICON, ICON_SMALL
                        icon_set = True
                        debug_log("Main window icon set via Windows API")
            except Exception as e:
                debug_log(f"Windows API icon setting failed: {e}")
        
        if not icon_set:
            debug_log("Warning: Could not set main window icon - all methods failed")
    
    def center_window(self):
        """Center the main window on screen"""
        self.root.update_idletasks()
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Get window dimensions
        window_width = 700
        window_height = 550
        
        # Calculate center position
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set window position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def show_centered_message(self, msg_type, title, message):
        """Show custom centered dialog that follows main window"""
        return CenteredMessageDialog(self.root, msg_type, title, message).show()
    
    def show_auto_close_message(self, msg_type, title, message, auto_close_ms=3000):
        """Show centered dialog that auto-closes after specified milliseconds"""
        dialog = CenteredMessageDialog(self.root, msg_type, title, message)
        
        # Auto-close the dialog after specified time
        def auto_close():
            try:
                if dialog.dialog and dialog.dialog.winfo_exists():
                    dialog.dialog.destroy()
            except:
                pass
        
        # Schedule auto-close
        self.root.after(auto_close_ms, auto_close)
        
        return dialog.show()
    
    def create_ui(self, parent):
        """Create mini tool UI with modern border"""
        
        # Modern UI container with border
        ui_container = ctk.CTkFrame(
            parent,
            fg_color="#2c3e50",
            border_color="#ffffff",
            border_width=2,
            corner_radius=0
        )
        ui_container.pack(fill="both", expand=True, padx=3, pady=3)
        
        # Header
        header = ctk.CTkFrame(
            ui_container,
            height=50,
            fg_color="#0495ce",
            corner_radius=0
        )
        header.pack(fill="x", padx=10, pady=(10, 5))
        header.pack_propagate(False)

        # Header content frame for title and license
        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Title with icon on left
        title_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        title_frame.pack(side="left")
        
        # Add icon using multiple methods to ensure it always appears
        icon_added = False
        if hasattr(self, 'icon_path') and self.icon_path:
            # Method 1: Try PIL/ImageTk for PNG files
            if not icon_added and self.icon_path.endswith('.png'):
                try:
                    from PIL import Image, ImageTk
                    icon_image = Image.open(self.icon_path)
                    icon_image = icon_image.resize((24, 24), Image.Resampling.LANCZOS)
                    self.header_icon = ImageTk.PhotoImage(icon_image)
                    
                    # Icon label
                    icon_label = ctk.CTkLabel(
                        title_frame,
                        image=self.header_icon,
                        text=""
                    )
                    icon_label.pack(side="left", padx=(0, 8))
                    icon_added = True
                    debug_log("Header icon loaded successfully with PIL")
                except Exception as e:
                    debug_log(f"PIL header icon failed: {e}")
            
            # Method 2: Try standard tkinter PhotoImage for PNG
            if not icon_added and self.icon_path.endswith('.png'):
                try:
                    import tkinter as tk
                    # Load with tkinter PhotoImage and subsample for resize
                    temp_image = tk.PhotoImage(file=self.icon_path)
                    # Calculate subsample factor to get ~24x24
                    scale_factor = max(1, temp_image.width() // 24, temp_image.height() // 24)
                    self.header_icon = temp_image.subsample(scale_factor, scale_factor)
                    
                    # Icon label
                    icon_label = ctk.CTkLabel(
                        title_frame,
                        image=self.header_icon,
                        text=""
                    )
                    icon_label.pack(side="left", padx=(0, 8))
                    icon_added = True
                    debug_log("Header icon loaded successfully with tkinter PhotoImage")
                except Exception as e:
                    debug_log(f"Tkinter PhotoImage header icon failed: {e}")
            
            # Method 3: Try .ico files directly with tkinter
            if not icon_added and self.icon_path.endswith('.ico'):
                try:
                    import tkinter as tk
                    # For ICO files, try to load directly
                    self.header_icon = tk.PhotoImage(file=self.icon_path)
                    
                    # Icon label
                    icon_label = ctk.CTkLabel(
                        title_frame,
                        image=self.header_icon,
                        text=""
                    )
                    icon_label.pack(side="left", padx=(0, 8))
                    icon_added = True
                    debug_log("Header icon loaded successfully from ICO")
                except Exception as e:
                    debug_log(f"ICO header icon failed: {e}")
        
        # Fallback: Use text-based icon if image loading failed
        if not icon_added:
            try:
                icon_label = ctk.CTkLabel(
                    title_frame,
                    text="🎬",  # Movie/video icon as fallback
                    font=ctk.CTkFont(size=20),
                    text_color="white"
                )
                icon_label.pack(side="left", padx=(0, 8))
                debug_log("Using fallback emoji icon in header")
            except Exception as e:
                debug_log(f"Even fallback icon failed: {e}")
        
        # Title text
        ctk.CTkLabel(
            title_frame,
            text="Cut Pro - Mini Tool",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        ).pack(side="left")
        
        # License activation on right
        self.create_header_license(header_content)
        
        # Main content
        main = ctk.CTkFrame(ui_container, 
                           fg_color="#34495e",
                           corner_radius=0)
        main.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # LEFT - Import
        self.create_import_panel(main)
        
        # RIGHT - Tools
        self.create_tools_panel(main)
        
        # Status
        self.create_status(ui_container)
    
    def create_header_license(self, parent):
        """Create license activation in header"""
        license_frame = ctk.CTkFrame(parent, fg_color="transparent")
        license_frame.pack(side="right")
        
        # License status label (first)
        self.license_status_label = ctk.CTkLabel(
            license_frame,
            text="License Not Activated",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="white"
        )
        self.license_status_label.pack(side="left", padx=(0, 5))
        
        # License key input (second)
        self.license_key_entry = ctk.CTkEntry(
            license_frame,
            placeholder_text="License_Key_Here",
            width=150,
            height=25,
            font=ctk.CTkFont(size=10),
            state="normal",  # Ensure it's enabled
            fg_color="white",
            text_color="black",
            border_color="#3498db",
            border_width=2
        )
        self.license_key_entry.pack(side="left", padx=5)
        
        # Ensure the entry field can receive focus
        self.license_key_entry.bind("<Button-1>", lambda e: self.license_key_entry.focus_set())
        
        # Activate button (third)
        self.activate_btn = ctk.CTkButton(
            license_frame,
            text="Activate",
            width=70,
            height=25,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2ecc71",
            hover_color="#27ae60",
            text_color="white",
            command=self.activate_license_action
        )
        self.activate_btn.pack(side="left", padx=5)
        
        # Load saved license code if exists
        saved_code = load_license_code()
        if saved_code:
            self.license_key_entry.insert(0, saved_code)
        
        # Check license status on startup
        self.check_license_status()
    
    def activate_license_action(self):
        """Handle license activation"""
        license_code = self.license_key_entry.get().strip()
        
        # Allow activation with saved key if field is empty
        if not license_code:
            saved_code = load_license_code()
            if not saved_code:
                self.show_centered_message("warning", "License Required", "Please enter your license key.")
                return
        
        self.activate_btn.configure(text="Activating...", state="disabled")
        self.license_status_label.configure(text="Activating license...")
        
        # Run activation in thread to prevent UI blocking
        threading.Thread(target=self._activate_license_worker, args=(license_code,), daemon=True).start()
    
    def _activate_license_worker(self, license_code):
        """License activation worker thread"""
        try:
            machine_id = get_machine_id()
            
            # First try to refresh existing token (if we have one)
            stored = load_token()
            if stored and stored.get("token"):
                success, result = refresh_license(stored["token"])
                if success:
                    # Update stored token with refreshed data
                    save_token(
                        result["token"],
                        result.get("expiresAt"),
                        stored.get("licenseCode"),
                        result.get("plan")
                    )
                    self.root.after(0, lambda: self._activation_success(result))
                    return
            
            # If refresh failed or no token, try activation
            # Use entered license code, or fall back to saved one if field is empty
            actual_license_code = license_code.strip()
            if not actual_license_code:
                actual_license_code = load_license_code()
            
            if not actual_license_code:
                self.root.after(0, lambda: self._activation_failed("Please enter a license key"))
                return
            
            # Activate license
            success, result = activate_license(actual_license_code, machine_id)
            if success:
                save_license_code(actual_license_code)
                save_token(
                    result["token"],
                    result.get("expiresAt"),
                    actual_license_code,
                    result.get("plan")
                )
                self.root.after(0, lambda: self._activation_success(result))
            else:
                self.root.after(0, lambda: self._activation_failed(result))
                
        except Exception as e:
            self.root.after(0, lambda: self._activation_failed(str(e)))
    
    def _activation_success(self, result):
        """Handle successful activation"""
        self.license_valid = True
        self.remaining_days = get_remaining_days(result.get("expiresAt"))
        
        # Update UI - disable both button and textbox to prevent re-activation during this session
        self.activate_btn.configure(text="Activated", state="disabled", fg_color="#27ae60", hover_color="#27ae60")
        self.license_key_entry.configure(state="disabled", fg_color="#e8e8e8", text_color="#7f8c8d")
        if isinstance(self.remaining_days, int):
            self.license_status_label.configure(text=f"License: {self.remaining_days} Days Remaining")
        else:
            self.license_status_label.configure(text=f"License: {self.remaining_days}")
        
        # Enable all tools
        self.enable_all_tools()
        
        # Show success in footer status instead of dialog
        if isinstance(self.remaining_days, int):
            self.update_status(f"✅ License activated! {self.remaining_days} days remaining")
        else:
            self.update_status(f"✅ License activated successfully!")
    
    def _activation_failed(self, error_msg):
        """Handle failed activation"""
        self.license_valid = False
        self.activate_btn.configure(text="Activate", state="normal", fg_color="#2ecc71")
        self.license_status_label.configure(text="License Not Activated")
        
        # Disable all tools
        self.disable_all_tools()
        
        self.show_centered_message("error", "Activation Failed", f"License activation failed:\n{error_msg}")
    
    def check_license_status(self):
        """Check current license status - always start disabled, require manual activation"""
        # Always start with license disabled - user must click Activate each time
        self.license_valid = False
        self.disable_all_tools()
        
        # Load saved license code but don't auto-activate
        saved_code = load_license_code()
        if saved_code:
            # Key is remembered but tools remain disabled
            # User must click Activate to unlock functionality
            pass
    
    def enable_all_tools(self):
        """Enable all tool buttons and import buttons"""
        if hasattr(self, 'tool_buttons'):
            for btn in self.tool_buttons:
                btn.configure(state="normal", fg_color="#0495ce", hover_color="#037ba3")
        
        # Enable import buttons
        if hasattr(self, 'import_files_btn'):
            self.import_files_btn.configure(state="normal", fg_color="#0495ce", hover_color="#037ba3")
        if hasattr(self, 'import_folder_btn'):
            self.import_folder_btn.configure(state="normal", fg_color="#0495ce", hover_color="#037ba3")
        if hasattr(self, 'browse_btn'):
            self.browse_btn.configure(state="normal", fg_color="#0495ce", hover_color="#037ba3")
        if hasattr(self, 'rename_btn'):
            self.rename_btn.configure(state="normal", fg_color="#0495ce", hover_color="#037ba3")
        if hasattr(self, 'clear_btn'):
            self.clear_btn.configure(state="normal", fg_color=["#C73E1D", "#A12E15"], hover_color=["#A12E15", "#8B2612"])
    
    def disable_all_tools(self):
        """Disable all tool buttons and import buttons except Activate"""
        if hasattr(self, 'tool_buttons'):
            for btn in self.tool_buttons:
                btn.configure(state="disabled", fg_color="#7f8c8d", hover_color="#7f8c8d")
        
        # Disable import buttons
        if hasattr(self, 'import_files_btn'):
            self.import_files_btn.configure(state="disabled", fg_color="#7f8c8d", hover_color="#7f8c8d")
        if hasattr(self, 'import_folder_btn'):
            self.import_folder_btn.configure(state="disabled", fg_color="#7f8c8d", hover_color="#7f8c8d")
        if hasattr(self, 'browse_btn'):
            self.browse_btn.configure(state="disabled", fg_color="#7f8c8d", hover_color="#7f8c8d")
        if hasattr(self, 'rename_btn'):
            self.rename_btn.configure(state="disabled", fg_color="#7f8c8d", hover_color="#7f8c8d")
        if hasattr(self, 'clear_btn'):
            self.clear_btn.configure(state="disabled", fg_color="#7f8c8d", hover_color="#7f8c8d")
    
    def check_ffmpeg_setup(self):
        """Check if FFmpeg is available, prompt for download if needed"""
        if not is_ffmpeg_available():
            # Show FFmpeg download dialog
            self.update_status("FFmpeg required for video processing")
            success = ensure_ffmpeg_available(self.root)
            if success:
                self.update_status("✅ FFmpeg installed successfully")
            else:
                self.update_status("FFmpeg setup cancelled - video processing unavailable")
        else:
            self.update_status("Ready - FFmpeg available")
    
    def get_ffmpeg_command(self):
        """Get the FFmpeg command to use (local or system)"""
        local_ffmpeg = get_ffmpeg_executable()
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
        else:
            # Fallback to system FFmpeg
            return "ffmpeg"
    
    def create_import_panel(self, parent):
        """Create import panel"""
        import_panel = ctk.CTkFrame(parent, width=300, fg_color="#3a526b")
        import_panel.pack(side="left", fill="y", padx=(0, 10))
        import_panel.pack_propagate(False)
        
        # Import section
        ctk.CTkLabel(import_panel, text="📁 Videos", 
                    font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=15)
        
        # Import buttons
        self.import_files_btn = ctk.CTkButton(import_panel, text="Import Files", height=40,
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.import_files)
        self.import_files_btn.pack(fill="x", padx=15, pady=5)
        
        self.import_folder_btn = ctk.CTkButton(import_panel, text="Import Folder", height=40,
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.import_folder)
        self.import_folder_btn.pack(fill="x", padx=15, pady=5)
        
        # Video List
        video_list_frame = ctk.CTkFrame(import_panel, fg_color="#2c3e50", height=150)
        video_list_frame.pack(fill="x", padx=15, pady=(5, 10))
        video_list_frame.pack_propagate(False)
        
        # List header with count
        self.video_files_header = ctk.CTkLabel(video_list_frame, text="📋 Video Files (0 Videos):", 
                    font=ctk.CTkFont(size=12, weight="bold"), 
                    text_color="#ffffff")
        self.video_files_header.pack(pady=(8, 5))
        
        # Scrollable frame for video list
        self.video_list_scrollable = ctk.CTkScrollableFrame(
            video_list_frame,
            height=110,
            fg_color="#34495e"
        )
        self.video_list_scrollable.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Custom file name
        ctk.CTkLabel(import_panel, text="📝 Custom File Name:", 
                    font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(pady=(3, 5))
        
        custom_name_frame = ctk.CTkFrame(import_panel, fg_color="transparent")
        custom_name_frame.pack(fill="x", padx=15)
        
        self.custom_name_entry = ctk.CTkEntry(custom_name_frame, placeholder_text="Optional: custom output name...")
        self.custom_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.rename_btn = ctk.CTkButton(custom_name_frame, text="Rename", width=70,
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.rename_files)
        self.rename_btn.pack(side="right")
        
        # Output
        ctk.CTkLabel(import_panel, text="💾 Output Folder:", 
                    font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(pady=(10, 5))
        
        output_frame = ctk.CTkFrame(import_panel, fg_color="transparent")
        output_frame.pack(fill="x", padx=15)
        
        self.output_entry = ctk.CTkEntry(output_frame, placeholder_text="Select folder...")
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.browse_btn = ctk.CTkButton(output_frame, text="Browse", width=70,
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.select_output)
        self.browse_btn.pack(side="right")
        
        # Clear button
        self.clear_btn = ctk.CTkButton(import_panel, text="Clear All", height=35,
                     fg_color=["#C73E1D", "#A12E15"],
                     hover_color=["#A12E15", "#8B2612"],
                     text_color="#ffffff",
                     command=self.clear_all)
        self.clear_btn.pack(fill="x", padx=15, pady=20)
    
    def create_tools_panel(self, parent):
        """Create tools panel"""
        tools_panel = ctk.CTkFrame(parent, fg_color="#3a526b")
        tools_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(tools_panel, text="🛠️ Tools", 
                    font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffffff").pack(pady=15)
        
        # Tools container
        tools_container = ctk.CTkFrame(tools_panel, fg_color="transparent")
        tools_container.pack(fill="both", expand=True, padx=15, pady=(0, 20))
        
        # Store tool buttons for enable/disable functionality
        self.tool_buttons = []
        
        # One button per tool category
        btn1 = ctk.CTkButton(tools_container, text="🔄 Rotate Video", height=50,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.show_rotate_options)
        btn1.pack(fill="x", pady=8)
        self.tool_buttons.append(btn1)
        
        btn2 = ctk.CTkButton(tools_container, text="📐 Crop Video", height=50,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.show_crop_options)
        btn2.pack(fill="x", pady=8)
        self.tool_buttons.append(btn2)
        
        btn3 = ctk.CTkButton(tools_container, text="🔀 Merge Videos", height=50,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.show_merge_options)
        btn3.pack(fill="x", pady=8)
        self.tool_buttons.append(btn3)
        
        btn4 = ctk.CTkButton(tools_container, text="⚡ Change Speed", height=50,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.show_speed_options)
        btn4.pack(fill="x", pady=8)
        self.tool_buttons.append(btn4)
        
        btn5 = ctk.CTkButton(tools_container, text="🎵 Extract Audio", height=50,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.show_audio_options)
        btn5.pack(fill="x", pady=8)
        self.tool_buttons.append(btn5)
        
        btn6 = ctk.CTkButton(tools_container, text="✨ Quality Enhancer", height=50,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.show_quality_options)
        btn6.pack(fill="x", pady=8)
        self.tool_buttons.append(btn6)
        
        btn7 = ctk.CTkButton(tools_container, text="🌊 Blur Background", height=50,
                     font=ctk.CTkFont(size=14, weight="bold"),
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.show_blur_background_options)
        btn7.pack(fill="x", pady=8)
        self.tool_buttons.append(btn7)
    
    def create_status(self, parent):
        """Create status bar"""
        status = ctk.CTkFrame(parent, 
                             height=35,
                             fg_color="#3a526b",
                             corner_radius=0)
        status.pack(fill="x", padx=10, pady=(5, 10))
        status.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(status, text="Ready", text_color="white")
        self.status_label.pack(side="left", padx=15, pady=8)
        
        self.progress = ctk.CTkProgressBar(status, width=200, height=8)
        self.progress.set(0)
    
    # Import functions
    def import_files(self):
        """Import files"""
        if not self.license_valid:
            self.show_centered_message("warning", "License Required", "Please activate your license to use this feature.")
            return
        
        files = filedialog.askopenfilenames(
            title="Select Videos",
            filetypes=[("Videos", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm")]
        )
        if files:
            self.add_videos(files)
    
    def import_folder(self):
        """Import folder"""
        if not self.license_valid:
            self.show_centered_message("warning", "License Required", "Please activate your license to use this feature.")
            return
        
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            exts = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
            files = [str(f) for f in Path(folder).rglob("*") if f.suffix.lower() in exts]
            
            if files:
                self.add_videos(files)
                self.update_status(f"Added {len(files)} videos")
                
                # Auto-create output folder for folder import
                if not self.output_folder:
                    self.auto_create_output_folder(folder)
            else:
                self.show_centered_message("info", "No Videos Found", "The selected folder doesn't contain any video files.\n\nPlease choose a folder with video files or import videos individually.")
    
    def add_videos(self, paths):
        """Add videos to list"""
        added = 0
        first_video_folder = None
        
        for path in paths:
            if not any(v['path'] == path for v in self.videos):
                try:
                    cap = cv2.VideoCapture(path)
                    if cap.isOpened():
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        cap.release()
                        
                        self.videos.append({
                            'path': path,
                            'name': os.path.basename(path),
                            'width': width,
                            'height': height
                        })
                        added += 1
                        
                        # Remember the folder of first video for auto output
                        if first_video_folder is None:
                            first_video_folder = os.path.dirname(path)
                            
                except:
                    pass
        
        if added > 0:
            self.update_count()
            self.update_status(f"Added {added} videos")
            
            # Auto-create output folder if not set
            if not self.output_folder and first_video_folder:
                self.auto_create_output_folder(first_video_folder)
    
    def clear_all(self):
        """Clear all videos from the list only (keeps output files)"""
        if not self.license_valid:
            self.show_centered_message("warning", "License Required", "Please activate your license to use this feature.")
            return

        debug_log("=== CLEAR ALL OPERATION STARTED ===")

        # Clear video list only
        self.videos.clear()
        self.update_count()

        # Reset output folder reference so it will be auto-created on next import
        old_output_folder = self.output_folder
        self.output_folder = ""
        debug_log(f"Reset output folder reference from '{old_output_folder}' to empty")

        self.update_status("✅ Cleared videos - Ready for new import")
            
        debug_log("=== CLEAR ALL OPERATION COMPLETED ===")
    
    def clear_output_folder(self):
        """Clear all files from the output folder"""
        debug_log(f"clear_output_folder called: output_folder={self.output_folder}")
        
        if not self.output_folder:
            debug_log("No output folder set")
            return 0
            
        if not os.path.exists(self.output_folder):
            debug_log(f"Output folder does not exist: {self.output_folder}")
            return 0
        
        cleared_count = 0
        try:
            # Get all files in output folder
            items = os.listdir(self.output_folder)
            debug_log(f"Found {len(items)} items in output folder: {items}")
            
            for filename in items:
                file_path = os.path.join(self.output_folder, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        cleared_count += 1
                        debug_log(f"✅ Deleted output file: {filename}")
                    elif os.path.isdir(file_path):
                        # Remove subdirectories (like Used folder)
                        import shutil
                        shutil.rmtree(file_path)
                        cleared_count += 1
                        debug_log(f"✅ Deleted output folder: {filename}")
                except Exception as e:
                    debug_log(f"❌ Error deleting {filename}: {e}")
            
            debug_log(f"Total cleared {cleared_count} items from output folder: {self.output_folder}")
            
        except Exception as e:
            debug_log(f"❌ Error clearing output folder: {e}")
        
        return cleared_count
    
    def update_count(self):
        """Update file count in video files header"""
        count = len(self.videos)
        self.video_files_header.configure(text=f"📋 Video Files ({count} Videos):")
        self.update_video_list()
    
    def update_video_list(self):
        """Update the video list display"""
        # Clear existing list items
        for widget in self.video_list_scrollable.winfo_children():
            widget.destroy()
        
        # Add each video to the list
        for i, video in enumerate(self.videos):
            video_item_frame = ctk.CTkFrame(self.video_list_scrollable, fg_color="#3a526b")
            video_item_frame.pack(fill="x", padx=2, pady=1)
            
            # Video info (name and resolution)
            video_name = video['name']
            if len(video_name) > 25:
                video_name = video_name[:22] + "..."
            
            video_info = f"{i+1}. {video_name}\n{video['width']}x{video['height']}"
            
            video_label = ctk.CTkLabel(
                video_item_frame,
                text=video_info,
                font=ctk.CTkFont(size=10),
                text_color="#ffffff",
                justify="left"
            )
            video_label.pack(side="left", fill="x", expand=True, padx=8, pady=4)
            
            # Remove button
            remove_btn = ctk.CTkButton(
                video_item_frame,
                text="×",
                width=25,
                height=25,
                font=ctk.CTkFont(size=14, weight="bold"),
                fg_color="#e74c3c",
                hover_color="#c0392b",
                text_color="#ffffff",
                command=lambda idx=i: self.remove_video(idx)
            )
            remove_btn.pack(side="right", padx=4, pady=4)
    
    def remove_video(self, index):
        """Remove a single video from the list"""
        if 0 <= index < len(self.videos):
            removed_video = self.videos.pop(index)
            self.update_count()
            self.update_status(f"Removed {removed_video['name']}")
    
    def auto_create_output_folder(self, video_folder):
        """Auto-create output folder based on video location"""
        try:
            debug_log(f"auto_create_output_folder called with video_folder: {video_folder}")
            
            # Create "Output" folder in the same location as videos
            auto_output_folder = os.path.join(video_folder, "Output")
            debug_log(f"Creating output folder: {auto_output_folder}")
            
            # Create folder if it doesn't exist
            os.makedirs(auto_output_folder, exist_ok=True)
            
            # Set as output folder
            self.output_folder = auto_output_folder
            debug_log(f"✅ Output folder set to: {self.output_folder}")
            
            # Update the output entry field in UI
            if hasattr(self, 'output_entry'):
                self.output_entry.delete(0, "end")
                self.output_entry.insert(0, auto_output_folder)
            
            # Update status to show the new output folder
            self.update_status(f"✅ Auto-created: {os.path.basename(auto_output_folder)}")
            
        except Exception as e:
            debug_log(f"❌ Error creating output folder: {e}")
            # Fallback - try to use the video folder itself
            self.output_folder = video_folder
            debug_log(f"Fallback: Using video folder as output: {self.output_folder}")
            self.update_status(f"Using source folder as output")
    
    def select_output(self):
        """Select output folder"""
        if not self.license_valid:
            self.show_centered_message("warning", "License Required", "Please activate your license to use this feature.")
            return
        
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder = folder
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)
    
    def rename_files(self):
        """Rename imported video files using custom name"""
        if not self.license_valid:
            self.show_centered_message("warning", "License Required", "Please activate your license to use this feature.")
            return
        
        if not self.videos:
            self.show_centered_message("warning", "No Videos Imported", "Please import video files first before using the rename function.\n\nUse 'Import Videos' or 'Import Folder' to add videos.")
            return
        
        custom_name = self.custom_name_entry.get().strip()
        if not custom_name:
            self.show_centered_message("warning", "No Custom Name", "Enter a custom name first.")
            return
        
        try:
            renamed_count = 0
            errors = []
            
            for i, video in enumerate(self.videos):
                try:
                    # Get original file info
                    original_path = video['path']
                    directory = os.path.dirname(original_path)
                    original_name = os.path.basename(original_path)
                    file_ext = os.path.splitext(original_name)[1]
                    
                    # Create new name
                    if len(self.videos) > 1:
                        new_name = f"{custom_name}_{i+1:02d}{file_ext}"
                    else:
                        new_name = f"{custom_name}{file_ext}"
                    
                    new_path = os.path.join(directory, new_name)
                    
                    # Skip if file would have same name
                    if original_path == new_path:
                        continue
                    
                    # Check if target file already exists
                    if os.path.exists(new_path):
                        errors.append(f"File already exists: {new_name}")
                        continue
                    
                    # Rename the file
                    os.rename(original_path, new_path)
                    
                    # Update video info in our list
                    video['path'] = new_path
                    video['name'] = new_name
                    
                    renamed_count += 1
                    debug_log(f"Renamed: {original_name} -> {new_name}")
                    
                except Exception as e:
                    errors.append(f"Error renaming {video['name']}: {str(e)}")
            
            # Show results
            if renamed_count > 0:
                if errors:
                    message = f"Renamed {renamed_count} files successfully.\n\nErrors:\n" + "\n".join(errors[:3])
                    if len(errors) > 3:
                        message += f"\n... and {len(errors) - 3} more errors"
                    self.show_centered_message("warning", "Partially Completed", message)
                else:
                    # Show success in footer status instead of dialog
                    self.update_status(f"✅ Successfully renamed {renamed_count} video files!")
            else:
                if errors:
                    error_msg = "No files were renamed.\n\nErrors:\n" + "\n".join(errors[:5])
                    if len(errors) > 5:
                        error_msg += f"\n... and {len(errors) - 5} more errors"
                else:
                    error_msg = "No files needed renaming."
                
                self.show_centered_message("info", "No Changes", error_msg)
                
        except Exception as e:
            self.show_centered_message("error", "Rename Error", f"An error occurred:\n{str(e)}")
            debug_log(f"Rename error: {e}")
    
    # Tool dialogs - Simple option selectors
    def show_rotate_options(self):
        """Show rotate options"""
        if not self.check_ready():
            return
        
        dialog = SimpleDialog(
            self,
            "🔄 Rotate Video",
            [
                ("90° (16:9→9:16)", lambda: self.process("rotate", 90)),
                ("180° (Upside Down)", lambda: self.process("rotate", 180)), 
                ("270° (9:16→16:9)", lambda: self.process("rotate", 270)),
                ("Flip Horizontal ⇄", lambda: self.process("flip", None))
            ]
        )
    
    def show_crop_options(self):
        """Show crop options"""
        if not self.check_ready():
            return
        
        dialog = SimpleDialog(
            self,
            "📐 Crop Video",
            [
                ("16:9 (YouTube)", lambda: self.process("crop", "16:9")),
                ("9:16 (TikTok)", lambda: self.process("crop", "9:16")),
                ("1:1 (Instagram)", lambda: self.process("crop", "1:1")),
                ("4:3 (Standard)", lambda: self.process("crop", "4:3"))
            ]
        )
    
    def show_merge_options(self):
        """Show merge options"""
        if not self.check_ready():
            return
        
        dialog = SimpleDialog(
            self,
            "🔀 Merge Videos",
            [
                ("Merge All → 1 Video", lambda: self.process("merge_all", None)),
                ("Merge Pairs (2→1)", lambda: self.process("merge_pairs", None)),
                ("Custom Merge", lambda: self.show_custom_merge_dialog())
            ]
        )
    
    def show_custom_merge_dialog(self):
        """Show custom merge dialog with textbox input"""
        dialog = CustomMergeDialog(self)
    
    def show_speed_options(self):
        """Show speed options"""
        if not self.check_ready():
            return
        
        dialog = SimpleDialog(
            self,
            "⚡ Change Speed", 
            [
                ("0.5x (Slow Motion)", lambda: self.process("speed", 0.5)),
                ("1.5x (Fast)", lambda: self.process("speed", 1.5)),
                ("2x (Double Speed)", lambda: self.process("speed", 2.0)),
                ("3x (Very Fast)", lambda: self.process("speed", 3.0))
            ]
        )
    
    def show_audio_options(self):
        """Show audio options"""
        if not self.check_ready():
            return
        
        dialog = SimpleDialog(
            self,
            "🎵 Extract Audio",
            [
                ("Extract MP3", lambda: self.process("audio", "mp3")),
                ("Extract WAV", lambda: self.process("audio", "wav"))
            ]
        )
    
    def show_quality_options(self):
        """Show quality enhancement options"""
        if not self.check_ready():
            return
        
        dialog = SimpleDialog(
            self,
            "✨ Quality Enhancer",
            [
                ("Enhance to 1080p (Full HD)", lambda: self.process("quality", "1080p")),
                ("Enhance to 2K (1440p)", lambda: self.process("quality", "2K")),
                ("Enhance to 4K (2160p)", lambda: self.process("quality", "4K")),
                ("Auto Enhance (Best Quality)", lambda: self.process("quality", "auto"))
            ]
        )
    
    def show_blur_background_options(self):
        """Show blur background conversion options"""
        if not self.check_ready():
            return
        
        dialog = SimpleDialog(
            self,
            "🌊 Blur Background",
            [
                ("9:16 → 16:9 (Add blur on sides)", lambda: self.show_blur_styles("horizontal")),
                ("16:9 → 9:16 (Add blur top/bottom)", lambda: self.show_blur_styles("vertical"))
            ]
        )
    
    def show_blur_styles(self, orientation):
        """Show quality options for blur background (Box Blur only)"""
        if orientation == "horizontal":
            title = "🌊 9:16 → 16:9 Quality Selection"
            operation = "blur_background"
        else:
            title = "🌊 16:9 → 9:16 Quality Selection"
            operation = "blur_background_reverse"
        
        dialog = SimpleDialog(
            self,
            title,
            [
                ("1080p (Full HD)", lambda: self.process(operation, "1080p_box")),
                ("2K (2560x1440)", lambda: self.process(operation, "2k_box")),
                ("4K (3840x2160)", lambda: self.process(operation, "4k_box"))
            ]
        )
    
    def check_ready(self):
        """Check if ready to process"""
        if not self.license_valid:
            self.show_centered_message("warning", "License Required", "Please activate your license to use this tool.")
            return False
        if not self.videos:
            self.show_centered_message("warning", "No Videos Available", "Please import video files before using tools.\n\nClick 'Import Videos' or 'Import Folder' to get started.")
            return False
        if not self.output_folder:
            self.show_centered_message("warning", "No Output", "Select output folder first.")
            return False
        return True
    
    def process(self, operation, parameter):
        """Process videos"""
        self.progress.pack(side="right", padx=10, pady=8)
        self.progress.set(0)
        
        thread = threading.Thread(target=self._process_worker, 
                                 args=(operation, parameter), daemon=True)
        thread.start()
    
    def _process_worker(self, operation, parameter):
        """Processing worker"""
        # Store current permanent status to restore later
        saved_permanent_status = self.permanent_status
        
        try:
            debug_log(f"Process worker started: operation={operation}, parameter={parameter}")
            total = len(self.videos)
            success = 0
            errors = []
            
            # Clear permanent status during processing so progress shows properly
            self.permanent_status = None
            
            # Test FFmpeg first
            test_result = subprocess.run([self.get_ffmpeg_command(), "-version"], capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            if test_result.returncode != 0:
                self.root.after(0, lambda: self.show_centered_message("error", "FFmpeg Error", "FFmpeg is not working properly."))
                return
            
            if operation == "merge_all":
                self.root.after(0, lambda: self.update_status("Merging all videos..."))
                paths = [v['path'] for v in self.videos]
                
                # Use custom name if provided
                custom_name = self.custom_name_entry.get().strip()
                if custom_name:
                    output_name = f"{custom_name}_merged_all.mp4"
                else:
                    output_name = "merged_all.mp4"
                
                output = os.path.join(self.output_folder, output_name)
                
                debug_log(f"Merging {len(paths)} videos to {output}")
                
                if self._merge_videos(paths, output):
                    success = 1
                    debug_log("Merge successful")
                else:
                    errors.append("Merge failed")
                    debug_log("Merge failed")
                    
                self.root.after(0, lambda: self.progress.set(1.0))
            
            elif operation == "merge_pairs":
                custom_name = self.custom_name_entry.get().strip()
                
                for i in range(0, len(self.videos), 2):
                    if i + 1 < len(self.videos):
                        v1, v2 = self.videos[i], self.videos[i + 1]
                        
                        # Use custom name if provided
                        if custom_name:
                            pair_number = i//2 + 1
                            output_name = f"{custom_name}_{pair_number:02d}.mp4"
                        else:
                            name1 = os.path.splitext(v1['name'])[0]
                            name2 = os.path.splitext(v2['name'])[0]
                            output_name = f"merged_{name1}_{name2}.mp4"
                        
                        output = os.path.join(self.output_folder, output_name)
                        
                        self.root.after(0, lambda: self.update_status(f"Merging pair {i//2 + 1}..."))
                        
                        debug_log(f"Merging pair: {v1['path']} + {v2['path']} -> {output}")
                        
                        if self._merge_videos([v1['path'], v2['path']], output):
                            success += 1
                            debug_log(f"Pair {i//2 + 1} merged successfully")
                        else:
                            errors.append(f"Pair {i//2 + 1} failed")
                            debug_log(f"Pair {i//2 + 1} failed")
                        
                        self.root.after(0, lambda p=(i+2)/total: self.progress.set(min(p, 1.0)))
            
            elif operation == "merge_custom":
                custom_name = self.custom_name_entry.get().strip()
                videos_per_group = parameter  # This will be the number from the textbox
                
                if videos_per_group <= 0 or videos_per_group > len(self.videos):
                    self.root.after(0, lambda: self.show_centered_message("error", "Invalid Input", 
                        f"Please enter a number between 1 and {len(self.videos)}"))
                    return
                
                group_count = 0
                for i in range(0, len(self.videos), videos_per_group):
                    group_videos = self.videos[i:i + videos_per_group]
                    group_count += 1
                    
                    # Create output filename
                    if custom_name:
                        output_name = f"{custom_name}_{group_count:02d}.mp4"
                    else:
                        output_name = f"merge_{group_count:02d}.mp4"
                    
                    output = os.path.join(self.output_folder, output_name)
                    
                    self.root.after(0, lambda gc=group_count: self.update_status(f"Merging group {gc}..."))
                    
                    video_paths = [v['path'] for v in group_videos]
                    debug_log(f"Merging group {group_count}: {len(group_videos)} videos -> {output}")
                    
                    if self._merge_videos(video_paths, output):
                        success += 1
                        debug_log(f"Group {group_count} merged successfully")
                    else:
                        errors.append(f"Group {group_count} failed")
                        debug_log(f"Group {group_count} failed")
                    
                    progress_value = min(i + videos_per_group, len(self.videos)) / len(self.videos)
                    self.root.after(0, lambda p=progress_value: self.progress.set(p))
            
            else:
                for i, video in enumerate(self.videos):
                    # Update status without auto-reset during processing
                    self.root.after(0, lambda i=i+1: self.update_status(f"Processing {i}/{total}...", auto_reset=False))
                    
                    debug_log(f"Processing video {i+1}: {video['name']} with operation {operation}")
                    
                    if self._process_video(video, operation, parameter):
                        success += 1
                        debug_log(f"Video {i+1} processed successfully")
                    else:
                        errors.append(f"Video {i+1}: {video['name']}")
                        debug_log(f"Video {i+1} failed")
                    
                    self.root.after(0, lambda p=(i+1)/total: self.progress.set(p))
            
            # Show detailed results
            if success > 0:
                # Move processed videos to "Used" folder
                self.root.after(0, lambda: self.move_videos_to_used_folder())
                
                # Show completion status with details (30-second delay)
                if len(errors) == 0:
                    # All successful
                    self.root.after(0, lambda: self.update_status(f"✅ Done! Processed {success}/{total} videos successfully", auto_reset=False))
                    # Return to permanent status after 30 seconds
                    self.root.after(30000, lambda: self.status_label.configure(text=saved_permanent_status or "Ready"))
                else:
                    # Mixed results
                    self.root.after(0, lambda: self.update_status(f"⚠️ Done! {success}/{total} successful, {len(errors)} failed", auto_reset=False))
                    # Return to permanent status after 30 seconds
                    self.root.after(30000, lambda: self.status_label.configure(text=saved_permanent_status or "Ready"))
            else:
                # All failed
                self.root.after(0, lambda: self.update_status(f"❌ Done! All {total} videos failed", auto_reset=False))
                # Return to permanent status after 30 seconds
                self.root.after(30000, lambda: self.status_label.configure(text=saved_permanent_status or "Ready"))
                
                error_msg = "No videos were processed.\\n\\n"
                if errors:
                    error_msg += "Errors:\\n" + "\\n".join(errors[:5])
                    if len(errors) > 5:
                        error_msg += f"\\n... and {len(errors) - 5} more errors"
                else:
                    error_msg += "Check that:\\n• Videos are valid\\n• Output folder is writable\\n• FFmpeg is working"
                
                self.root.after(0, lambda: self.show_centered_message("error", "Processing Failed", error_msg))
        
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            debug_log(error_msg)
            self.root.after(0, lambda: self.show_centered_message("error", "Error", error_msg))
        finally:
            # Restore permanent status reference (but don't change display - let completion messages show for 30s)
            self.root.after(0, lambda: setattr(self, 'permanent_status', saved_permanent_status))
            self.root.after(2000, lambda: self.progress.pack_forget())
    
    def _process_video(self, video, operation, parameter):
        """Process single video"""
        input_path = video['path']
        
        # Use custom name if provided, otherwise use original name
        custom_name = self.custom_name_entry.get().strip()
        if custom_name:
            base_name = custom_name
        else:
            base_name = os.path.splitext(video['name'])[0]
        
        # If processing multiple videos with custom name, add index
        if len(self.videos) > 1 and custom_name:
            video_index = self.videos.index(video) + 1
            base_name = f"{custom_name}_{video_index:02d}"
        
        try:
            debug_log(f"_process_video: operation={operation}, parameter={parameter}, base_name={base_name}")
            if operation == "rotate":
                output = f"{base_name}_rot{parameter}.mp4"
                return self._ffmpeg_rotate(input_path, output, parameter)
            
            elif operation == "flip":
                output = f"{base_name}_flipped.mp4"
                return self._ffmpeg_flip(input_path, output)
            
            elif operation == "crop":
                output = f"{base_name}_{parameter.replace(':', 'x')}.mp4"
                return self._ffmpeg_crop(input_path, output, parameter)
            
            elif operation == "speed":
                output = f"{base_name}_{parameter}x.mp4"
                return self._ffmpeg_speed(input_path, output, parameter)
            
            elif operation == "audio":
                output = f"{base_name}.{parameter}"
                return self._ffmpeg_audio(input_path, output, parameter)
            
            elif operation == "quality":
                if parameter == "1080p":
                    output = f"{base_name}_1080p.mp4"
                elif parameter == "2K":
                    output = f"{base_name}_2K.mp4"
                elif parameter == "4K":
                    output = f"{base_name}_4K.mp4"
                else:  # auto
                    output = f"{base_name}_enhanced.mp4"
                return self._ffmpeg_quality_enhance(input_path, output, parameter)
            
            elif operation == "blur_background":
                if '_' in parameter:
                    quality, style = parameter.split('_', 1)
                    output = f"{base_name}_{quality.upper()}_box_16x9.mp4"
                else:
                    output = f"{base_name}_{parameter}_16x9.mp4"
                return self._ffmpeg_blur_background(input_path, output, parameter)
            
            elif operation == "blur_background_reverse":
                if '_' in parameter:
                    quality, style = parameter.split('_', 1)
                    output = f"{base_name}_{quality.upper()}_box_9x16.mp4"
                else:
                    output = f"{base_name}_{parameter}_9x16.mp4"
                return self._ffmpeg_blur_background_reverse(input_path, output, parameter)
        
        except Exception as e:
            debug_log(f"Error: {e}")
        
        return False
    
    # FFmpeg functions with better error handling
    def _ffmpeg_rotate(self, input_path, output_name, angle):
        """Rotate video"""
        output = os.path.join(self.output_folder, output_name)
        filters = {90: "transpose=1", 180: "transpose=2,transpose=2", 270: "transpose=2"}
        
        # Get GPU encoders and use GPU if available
        gpu_encoders = detect_gpu_encoders()
        
        if gpu_encoders.get('nvidia'):
            # Use NVIDIA GPU encoder
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", filters[angle],
                "-c:v", "h264_nvenc",
                "-preset", "fast",
                "-cq", "23",
                "-c:a", "copy",
                "-y", output
            ]
        elif gpu_encoders.get('amd'):
            # Use AMD GPU encoder
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", filters[angle],
                "-c:v", "h264_amf",
                "-quality", "balanced",
                "-rc", "cqp",
                "-qp_i", "23",
                "-qp_p", "23",
                "-c:a", "copy",
                "-y", output
            ]
        elif gpu_encoders.get('intel'):
            # Use Intel GPU encoder
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", filters[angle],
                "-c:v", "h264_qsv",
                "-preset", "balanced",
                "-global_quality", "23",
                "-c:a", "copy",
                "-y", output
            ]
        else:
            # CPU fallback
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", filters[angle],
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "copy",
                "-y", output
            ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            if result.returncode != 0:
                debug_log(f"FFmpeg rotate error: {result.stderr}")
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            debug_log("FFmpeg timeout during rotation")
            return False
        except Exception as e:
            debug_log(f"Rotation error: {e}")
            return False
    
    def _ffmpeg_flip(self, input_path, output_name):
        """Flip video"""
        output = os.path.join(self.output_folder, output_name)
        
        # Get GPU encoders and use GPU if available
        gpu_encoders = detect_gpu_encoders()
        
        if gpu_encoders.get('nvidia'):
            # Use NVIDIA GPU encoder
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", "hflip",
                "-c:v", "h264_nvenc",
                "-preset", "fast",
                "-cq", "23",
                "-c:a", "copy",
                "-y", output
            ]
        elif gpu_encoders.get('amd'):
            # Use AMD GPU encoder
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", "hflip",
                "-c:v", "h264_amf",
                "-quality", "balanced",
                "-rc", "cqp",
                "-qp_i", "23",
                "-qp_p", "23",
                "-c:a", "copy",
                "-y", output
            ]
        elif gpu_encoders.get('intel'):
            # Use Intel GPU encoder
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", "hflip",
                "-c:v", "h264_qsv",
                "-preset", "balanced",
                "-global_quality", "23",
                "-c:a", "copy",
                "-y", output
            ]
        else:
            # CPU fallback
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", "hflip",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "copy",
                "-y", output
            ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            if result.returncode != 0:
                debug_log(f"FFmpeg flip error: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            debug_log(f"Flip error: {e}")
            return False
    
    def _ffmpeg_crop(self, input_path, output_name, ratio):
        """Crop video"""
        output = os.path.join(self.output_folder, output_name)
        
        try:
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                debug_log(f"Cannot open video: {input_path}")
                return False
                
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            ratios = {"16:9": 16/9, "9:16": 9/16, "1:1": 1, "4:3": 4/3}
            target = ratios.get(ratio, 16/9)
            current = width / height
            
            if current > target:
                new_width = int(height * target)
                x = (width - new_width) // 2
                crop = f"crop={new_width}:{height}:{x}:0"
            else:
                new_height = int(width / target)
                y = (height - new_height) // 2
                crop = f"crop={width}:{new_height}:0:{y}"
            
            # Use GPU acceleration for video cropping
            gpu_encoders = detect_gpu_encoders()
            if gpu_encoders.get('nvidia'):
                cmd = [
                    self.get_ffmpeg_command(), "-i", input_path,
                    "-vf", crop,
                    "-c:v", "h264_nvenc",  # NVIDIA GPU encoder
                    "-preset", "fast",     # Fast preset for cropping
                    "-cq", "21",          # High quality
                    "-c:a", "copy",       # Copy audio without re-encoding
                    "-y", output
                ]
                debug_log("Using NVIDIA GPU acceleration for video cropping")
            elif gpu_encoders.get('amd'):
                cmd = [
                    self.get_ffmpeg_command(), "-i", input_path,
                    "-vf", crop,
                    "-c:v", "h264_amf",
                    "-quality", "balanced",
                    "-rc", "cqp",
                    "-qp_i", "21",
                    "-qp_p", "21",
                    "-c:a", "copy",
                    "-y", output
                ]
                debug_log("Using AMD GPU acceleration for video cropping")
            elif gpu_encoders.get('intel'):
                cmd = [
                    self.get_ffmpeg_command(), "-i", input_path,
                    "-vf", crop,
                    "-c:v", "h264_qsv",
                    "-preset", "balanced",
                    "-global_quality", "21",
                    "-c:a", "copy",
                    "-y", output
                ]
                debug_log("Using Intel GPU acceleration for video cropping")
            else:
                cmd = [
                    self.get_ffmpeg_command(), "-i", input_path,
                    "-vf", crop,
                    "-c:v", "libx264",    # CPU fallback
                    "-preset", "fast",
                    "-crf", "21",
                    "-c:a", "copy",
                    "-y", output
                ]
                debug_log("Using CPU encoding for cropping (GPU not available)")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            if result.returncode != 0:
                debug_log(f"FFmpeg crop error: {result.stderr}")
            return result.returncode == 0
            
        except Exception as e:
            debug_log(f"Crop error: {e}")
            return False
    
    def _ffmpeg_speed(self, input_path, output_name, factor):
        """Change speed"""
        output = os.path.join(self.output_folder, output_name)
        
        video_filter = f"setpts={1/factor}*PTS"
        audio_filter = f"atempo={factor}"
        
        # Use GPU acceleration for speed changes
        gpu_encoders = detect_gpu_encoders()
        if gpu_encoders.get('nvidia'):
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", video_filter,
                "-af", audio_filter,
                "-c:v", "h264_nvenc",  # NVIDIA GPU encoder
                "-preset", "fast",     # Fast preset for speed changes
                "-cq", "23",          # Good quality
                "-y", output
            ]
            debug_log("Using NVIDIA GPU acceleration for speed change")
        elif gpu_encoders.get('amd'):
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", video_filter, "-af", audio_filter,
                "-c:v", "h264_amf",
                "-quality", "balanced",
                "-rc", "cqp",
                "-qp_i", "23",
                "-qp_p", "23",
                "-y", output
            ]
            debug_log("Using AMD GPU acceleration for speed change")
        elif gpu_encoders.get('intel'):
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", video_filter, "-af", audio_filter,
                "-c:v", "h264_qsv",
                "-preset", "balanced",
                "-global_quality", "23",
                "-y", output
            ]
            debug_log("Using Intel GPU acceleration for speed change")
        else:
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vf", video_filter,
                "-af", audio_filter,
                "-c:v", "libx264",    # CPU fallback
                "-preset", "fast",
                "-crf", "23",
                "-y", output
            ]
            debug_log("Using CPU encoding for speed change (GPU not available)")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            if result.returncode != 0:
                debug_log(f"FFmpeg speed error: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            debug_log(f"Speed error: {e}")
            return False
    
    def _ffmpeg_audio(self, input_path, output_name, format_type):
        """Extract audio"""
        output = os.path.join(self.output_folder, output_name)
        
        if format_type == "mp3":
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vn", "-acodec", "libmp3lame", "-ab", "192k",
                "-y", output
            ]
        else:  # wav
            cmd = [
                self.get_ffmpeg_command(), "-i", input_path,
                "-vn", "-acodec", "pcm_s16le",
                "-y", output
            ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            if result.returncode != 0:
                debug_log(f"FFmpeg audio error: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            debug_log(f"Audio error: {e}")
            return False
    
    def _ffmpeg_quality_enhance(self, input_path, output_name, resolution):
        """Enhance video quality using FFmpeg while preserving aspect ratio"""
        output = os.path.join(self.output_folder, output_name)
        
        try:
            # Ensure output directory exists
            os.makedirs(self.output_folder, exist_ok=True)
            # Get input video info first
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                debug_log(f"Cannot open video: {input_path}")
                return False
                
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # Calculate aspect ratio
            aspect_ratio = width / height
            debug_log(f"Input video: {width}x{height}, aspect ratio: {aspect_ratio:.3f}")
            
            # Determine target resolution while preserving aspect ratio
            if resolution == "1080p":
                if aspect_ratio > 1:  # Landscape (16:9, etc.)
                    target_height = 1080
                    target_width = int(target_height * aspect_ratio)
                    # Round to even numbers for codec compatibility
                    target_width = target_width - (target_width % 2)
                else:  # Portrait (9:16, etc.) or square
                    target_width = 1080
                    target_height = int(target_width / aspect_ratio)
                    target_height = target_height - (target_height % 2)
                    
            elif resolution == "2K":
                if aspect_ratio > 1:  # Landscape
                    target_height = 1440
                    target_width = int(target_height * aspect_ratio)
                    target_width = target_width - (target_width % 2)
                else:  # Portrait or square
                    target_width = 1440
                    target_height = int(target_width / aspect_ratio)
                    target_height = target_height - (target_height % 2)
                    
            elif resolution == "4K":
                if aspect_ratio > 1:  # Landscape
                    target_height = 2160
                    target_width = int(target_height * aspect_ratio)
                    target_width = target_width - (target_width % 2)
                else:  # Portrait or square
                    target_width = 2160
                    target_height = int(target_width / aspect_ratio)
                    target_height = target_height - (target_height % 2)
                    
            else:  # auto - enhance by 2x while preserving aspect ratio
                target_width = width * 2
                target_height = height * 2
                # Round to even numbers
                target_width = target_width - (target_width % 2)
                target_height = target_height - (target_height % 2)
            
            # Determine if we need to upscale
            current_pixels = width * height
            target_pixels = target_width * target_height
            
            if current_pixels >= target_pixels:
                debug_log(f"Video already at or above {resolution} resolution")
                # Just improve quality without upscaling
                # Try NVIDIA GPU acceleration first, fallback to CPU if needed
                gpu_encoders = detect_gpu_encoders()
                if gpu_encoders.get('nvidia'):
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-c:v", "h264_nvenc",  # NVIDIA GPU encoder
                        "-preset", "slow",     # High quality preset for NVENC
                        "-cq", "18",          # Constant quality for NVENC
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using NVIDIA GPU acceleration for quality enhancement")
                elif gpu_encoders.get('amd'):
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-c:v", "h264_amf",
                        "-quality", "quality",
                        "-rc", "cqp",
                        "-qp_i", "18",
                        "-qp_p", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using AMD GPU acceleration for quality enhancement")
                elif gpu_encoders.get('intel'):
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-c:v", "h264_qsv",
                        "-preset", "slower",
                        "-global_quality", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using Intel GPU acceleration for quality enhancement")
                else:
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-c:v", "libx264",    # CPU fallback
                        "-preset", "slow",
                        "-crf", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using CPU encoding (GPU not available)")
                debug_log(f"Quality improvement: {width}x{height} (no upscaling needed)")
            else:
                # Upscale with GPU acceleration for maximum speed
                gpu_encoders = detect_gpu_encoders()
                if gpu_encoders.get('nvidia'):
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-vf", f"scale={target_width}:{target_height}",  # Standard scaling (works with all GPUs)
                        "-c:v", "h264_nvenc",  # NVIDIA GPU encoder
                        "-preset", "slow",     # High quality preset for NVENC
                        "-cq", "18",          # Constant quality for NVENC
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using NVIDIA GPU acceleration for upscaling")
                elif gpu_encoders.get('amd'):
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-vf", f"scale={target_width}:{target_height}:flags=lanczos",
                        "-c:v", "h264_amf",
                        "-quality", "quality",
                        "-rc", "cqp",
                        "-qp_i", "18",
                        "-qp_p", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using AMD GPU acceleration for upscaling")
                elif gpu_encoders.get('intel'):
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-vf", f"scale={target_width}:{target_height}:flags=lanczos",
                        "-c:v", "h264_qsv",
                        "-preset", "slower",
                        "-global_quality", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using Intel GPU acceleration for upscaling")
                else:
                    cmd = [
                        self.get_ffmpeg_command(), "-i", input_path,
                        "-vf", f"scale={target_width}:{target_height}:flags=lanczos",  # CPU scaling
                        "-c:v", "libx264",    # CPU encoder
                        "-preset", "slow",
                        "-crf", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-y", output
                    ]
                    debug_log("Using CPU encoding for upscaling (GPU not available)")
                debug_log(f"Upscaling: {width}x{height} -> {target_width}x{target_height} (aspect ratio preserved)")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)  # Longer timeout for quality processing
            if result.returncode != 0:
                debug_log(f"FFmpeg quality enhance error: {result.stderr}")
            return result.returncode == 0
            
        except Exception as e:
            debug_log(f"Quality enhance error: {e}")
            return False
    
    def _ffmpeg_blur_background(self, input_path, output_name, blur_param):
        """Convert 9:16 video to 16:9 with blurred background"""
        output = os.path.join(self.output_folder, output_name)
        
        try:
            # Check if FFmpeg is available first
            ffmpeg_cmd = self.get_ffmpeg_command()
            debug_log(f"Using FFmpeg: {ffmpeg_cmd}")
            if not os.path.exists(ffmpeg_cmd) and ffmpeg_cmd != "ffmpeg":
                debug_log("FFmpeg not found locally, checking if download is needed")
                if not is_ffmpeg_available():
                    debug_log("FFmpeg not available, triggering download")
                    # Trigger FFmpeg download
                    import tkinter.messagebox as msgbox
                    if msgbox.askyesno("FFmpeg Required", "FFmpeg is required for blur background. Download now?"):
                        if not self.download_ffmpeg():
                            msgbox.showerror("Error", "Failed to download FFmpeg")
                            return False
                    else:
                        return False
            # Parse quality and blur style from parameter
            if '_' in blur_param:
                quality, blur_style = blur_param.split('_', 1)
            else:
                quality = "1080p"
                blur_style = blur_param
            
            # Ensure output directory exists
            os.makedirs(self.output_folder, exist_ok=True)
            
            # Get input video info first
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                debug_log(f"Cannot open video: {input_path}")
                return False
                
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # Calculate aspect ratio
            aspect_ratio = width / height
            debug_log(f"Input video: {width}x{height}, aspect ratio: {aspect_ratio:.3f}")
            
            # Check if video is already 16:9 or wider
            if aspect_ratio >= (16/9):
                debug_log("Video is already 16:9 or wider, no conversion needed")
                # Just copy the file
                import shutil
                shutil.copy2(input_path, output)
                return True
            
            # Set target resolution based on quality
            if quality == "4k":
                target_height = 2160
                target_width = 3840
            elif quality == "2k":
                target_height = 1440
                target_width = 2560
            else:  # 1080p
                target_height = 1080
                target_width = 1920
            
            # Make dimensions even for codec compatibility
            target_width = target_width - (target_width % 2)
            target_height = target_height - (target_height % 2)
            
            # Calculate main video dimensions to fit within target
            scale_factor = min(target_width / width, target_height / height)
            main_width = int(width * scale_factor)
            main_height = int(height * scale_factor)
            main_width = main_width - (main_width % 2)
            main_height = main_height - (main_height % 2)
            
            debug_log(f"Target output: {target_width}x{target_height} ({quality.upper()}, main: {main_width}x{main_height})")
            
            # Box blur background (only blur style used)
            blur_amount = "20"
            filter_complex = (
                f"[0:v]scale={target_width}:{target_height}[bg];"
                f"[bg]boxblur={blur_amount}:{blur_amount}[bg_blur];"
                f"[0:v]scale={main_width}:{main_height}[main];"
                f"[bg_blur][main]overlay=(W-w)/2:(H-h)/2"
            )
            
            # Get GPU acceleration settings
            ffmpeg_cmd = self.get_ffmpeg_command()
            gpu_settings = get_gpu_settings(ffmpeg_cmd)
            
            # Build command with GPU acceleration
            cmd = [ffmpeg_cmd, "-i", input_path, "-filter_complex", filter_complex]
            
            # Add encoder and settings
            cmd.extend(["-c:v", gpu_settings['encoder']])
            cmd.extend(["-preset", gpu_settings['preset']])
            
            # Add GPU-specific encoding arguments
            if gpu_settings['gpu_type'] == 'cpu':
                cmd.extend(["-crf", "23"])
            else:
                cmd.extend(gpu_settings['extra_args'])
            
            # Add audio and output settings
            cmd.extend(["-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-y", output])
            
            debug_log(f"Blur background conversion: {width}x{height} -> {target_width}x{target_height} (Box Blur, {gpu_settings['gpu_type'].upper()})")
            debug_log(f"FFmpeg command: {' '.join(cmd)}")
            debug_log(f"Filter complex: {filter_complex}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            debug_log(f"FFmpeg return code: {result.returncode}")
            if result.stdout:
                debug_log(f"FFmpeg stdout: {result.stdout}")
            if result.returncode != 0:
                debug_log(f"FFmpeg blur background error: {result.stderr}")
                # Show error to user
                import tkinter.messagebox as msgbox
                msgbox.showerror("Blur Background Error", f"FFmpeg processing failed:\n{result.stderr[:200]}...")
            return result.returncode == 0
            
        except Exception as e:
            debug_log(f"Blur background error: {e}")
            return False
    
    def _ffmpeg_blur_background_reverse(self, input_path, output_name, blur_param):
        """Convert 16:9 video to 9:16 with blurred top/bottom"""
        output = os.path.join(self.output_folder, output_name)
        
        try:
            # Check if FFmpeg is available first
            ffmpeg_cmd = self.get_ffmpeg_command()
            debug_log(f"Using FFmpeg: {ffmpeg_cmd}")
            if not os.path.exists(ffmpeg_cmd) and ffmpeg_cmd != "ffmpeg":
                debug_log("FFmpeg not found locally, checking if download is needed")
                if not is_ffmpeg_available():
                    debug_log("FFmpeg not available, triggering download")
                    # Trigger FFmpeg download
                    import tkinter.messagebox as msgbox
                    if msgbox.askyesno("FFmpeg Required", "FFmpeg is required for reverse blur background. Download now?"):
                        if not self.download_ffmpeg():
                            msgbox.showerror("Error", "Failed to download FFmpeg")
                            return False
                    else:
                        return False
            # Parse quality and blur style from parameter
            if '_' in blur_param:
                quality, blur_style = blur_param.split('_', 1)
            else:
                quality = "1080p"
                blur_style = blur_param
            
            # Ensure output directory exists
            os.makedirs(self.output_folder, exist_ok=True)
            
            # Get input video info first
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                debug_log(f"Cannot open video: {input_path}")
                return False
                
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            # Calculate aspect ratio
            aspect_ratio = width / height
            debug_log(f"Input video: {width}x{height}, aspect ratio: {aspect_ratio:.3f}")
            
            # Check if video is already 9:16 or taller
            if aspect_ratio <= (9/16):
                debug_log("Video is already 9:16 or taller, no conversion needed")
                # Just copy the file
                import shutil
                shutil.copy2(input_path, output)
                return True
            
            # Set target resolution based on quality
            if quality == "4k":
                target_width = 2160
                target_height = 3840
            elif quality == "2k":
                target_width = 1440
                target_height = 2560
            else:  # 1080p
                target_width = 1080
                target_height = 1920
            
            # Make dimensions even for codec compatibility
            target_width = target_width - (target_width % 2)
            target_height = target_height - (target_height % 2)
            
            # Calculate main video dimensions to fit within target
            scale_factor = min(target_width / width, target_height / height)
            main_width = int(width * scale_factor)
            main_height = int(height * scale_factor)
            main_width = main_width - (main_width % 2)
            main_height = main_height - (main_height % 2)
            
            debug_log(f"Target output: {target_width}x{target_height} ({quality.upper()}, main: {main_width}x{main_height})")
            
            # Box blur background (only blur style used)
            blur_amount = "20"
            filter_complex = (
                f"[0:v]scale={target_width}:{target_height}[bg];"
                f"[bg]boxblur={blur_amount}:{blur_amount}[bg_blur];"
                f"[0:v]scale={main_width}:{main_height}[main];"
                f"[bg_blur][main]overlay=(W-w)/2:(H-h)/2"
            )
            
            # Get GPU acceleration settings
            ffmpeg_cmd = self.get_ffmpeg_command()
            gpu_settings = get_gpu_settings(ffmpeg_cmd)
            
            # Build command with GPU acceleration
            cmd = [ffmpeg_cmd, "-i", input_path, "-filter_complex", filter_complex]
            
            # Add encoder and settings
            cmd.extend(["-c:v", gpu_settings['encoder']])
            cmd.extend(["-preset", gpu_settings['preset']])
            
            # Add GPU-specific encoding arguments
            if gpu_settings['gpu_type'] == 'cpu':
                cmd.extend(["-crf", "23"])
            else:
                cmd.extend(gpu_settings['extra_args'])
            
            # Add audio and output settings
            cmd.extend(["-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-y", output])
            
            debug_log(f"Reverse blur background conversion: {width}x{height} -> {target_width}x{target_height} (Box Blur, {gpu_settings['gpu_type'].upper()})")
            debug_log(f"FFmpeg command: {' '.join(cmd)}")
            debug_log(f"Filter complex: {filter_complex}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            debug_log(f"FFmpeg return code: {result.returncode}")
            if result.stdout:
                debug_log(f"FFmpeg stdout: {result.stdout}")
            if result.returncode != 0:
                debug_log(f"FFmpeg reverse blur background error: {result.stderr}")
                # Show error to user
                import tkinter.messagebox as msgbox
                msgbox.showerror("Reverse Blur Background Error", f"FFmpeg processing failed:\n{result.stderr[:200]}...")
            return result.returncode == 0
            
        except Exception as e:
            debug_log(f"Reverse blur background error: {e}")
            return False
    
    def _merge_videos(self, paths, output_path):
        """Merge videos"""
        filelist_path = "temp_merge_list.txt"
        try:
            # Create file list with proper format
            with open(filelist_path, "w", encoding="utf-8") as f:
                for path in paths:
                    # Normalize path and escape properly for FFmpeg
                    normalized_path = os.path.normpath(path).replace("\\", "/")
                    f.write(f"file '{normalized_path}'\n")
            
            # Debug: log the file list content
            debug_log(f"File list content:")
            with open(filelist_path, "r") as f:
                content = f.read()
                debug_log(content)
            
            cmd = [
                self.get_ffmpeg_command(), "-f", "concat", "-safe", "0",
                "-i", filelist_path,
                "-c", "copy",
                "-y", output_path
            ]
            
            debug_log(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            
            if result.returncode != 0:
                debug_log(f"FFmpeg merge error: {result.stderr}")
                return False
            
            debug_log(f"Merge successful: {output_path}")
            return True
            
        except Exception as e:
            debug_log(f"Merge error: {e}")
            return False
        finally:
            # Clean up temp file
            if os.path.exists(filelist_path):
                try:
                    os.remove(filelist_path)
                except:
                    pass
    
    def move_videos_to_used_folder(self):
        """Move all processed videos to 'Used' folder"""
        try:
            if not self.videos:
                return
            
            # Get the folder where first video is located
            first_video_folder = os.path.dirname(self.videos[0]['path'])
            used_folder = os.path.join(first_video_folder, "Used")
            
            # Create Used folder if it doesn't exist
            os.makedirs(used_folder, exist_ok=True)
            
            moved_count = 0
            
            for video in self.videos:
                try:
                    original_path = video['path']
                    filename = os.path.basename(original_path)
                    new_path = os.path.join(used_folder, filename)
                    
                    # Move file to Used folder
                    if os.path.exists(original_path):
                        # If file already exists in Used folder, add number suffix
                        counter = 1
                        base_name, ext = os.path.splitext(filename)
                        while os.path.exists(new_path):
                            new_filename = f"{base_name}_{counter}{ext}"
                            new_path = os.path.join(used_folder, new_filename)
                            counter += 1
                        
                        os.rename(original_path, new_path)
                        moved_count += 1
                        debug_log(f"Moved: {filename} → Used/{os.path.basename(new_path)}")
                        
                except Exception as e:
                    debug_log(f"Error moving {video['name']}: {e}")
            
            if moved_count > 0:
                self.update_status(f"Moved {moved_count} videos to 'Used' folder")
                debug_log(f"Successfully moved {moved_count} videos to: {used_folder}")
            
        except Exception as e:
            debug_log(f"Error moving videos to Used folder: {e}")
    
    def update_status(self, msg, auto_reset=True):
        """Update status temporarily"""
        self.status_label.configure(text=msg)
        
        # Cancel any pending status reset
        if hasattr(self, '_status_reset_timer') and self._status_reset_timer:
            self.root.after_cancel(self._status_reset_timer)
            self._status_reset_timer = None
        
        # Reset to permanent status or default "Ready" after 3 seconds (if auto_reset is True)
        if auto_reset:
            self._status_reset_timer = self.root.after(3000, lambda: self.status_label.configure(text=self.permanent_status or "Ready"))
    
    def set_permanent_status(self, msg):
        """Set permanent status that doesn't reset"""
        self.permanent_status = msg
        self.status_label.configure(text=msg)
    
    def test_ffmpeg(self):
        """Test FFmpeg installation"""
        try:
            # Test FFmpeg with a simple command
            result = subprocess.run([self.get_ffmpeg_command(), "-version"], 
                                  capture_output=True, text=True, timeout=10, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0)
            
            if result.returncode == 0:
                # Temporary status - GPU initialization will set permanent status later
                self.update_status("FFmpeg detected - Initializing...")
                return True
            else:
                self.set_permanent_status("FFmpeg test failed")
                return False
                
        except FileNotFoundError:
            self.show_centered_message("error", "FFmpeg Not Found", 
                               "FFmpeg is not installed or not in system PATH.\\n\\n" +
                               "Please install FFmpeg from https://ffmpeg.org/download.html\\n" +
                               "and add it to your system PATH.")
            self.update_status("FFmpeg not found")
            return False
        except Exception as e:
            self.show_centered_message("error", "FFmpeg Error", f"FFmpeg test failed: {e}")
            self.update_status("FFmpeg error")
            return False
    
    def force_taskbar_icon(self):
        """Force taskbar icon update using multiple methods"""
        if not self.icon_path or getattr(sys, 'frozen', False):
            return
            
        try:
            if sys.platform.startswith('win'):
                import ctypes
                from ctypes import wintypes
                
                # Get window handle - try multiple methods
                hwnd = None
                try:
                    # Method 1: Direct from tkinter
                    hwnd = int(self.root.frame(), 16) if hasattr(self.root, 'frame') else None
                except:
                    pass
                    
                if not hwnd:
                    try:
                        # Method 2: From winfo_id
                        hwnd = self.root.winfo_id()
                        # Convert to actual window handle
                        hwnd = ctypes.windll.user32.GetAncestor(hwnd, 2)  # GA_ROOT
                    except:
                        pass
                
                if not hwnd:
                    try:
                        # Method 3: Find by window title
                        hwnd = ctypes.windll.user32.FindWindowW(None, "Cut Pro - Mini Tool")
                    except:
                        pass
                
                if hwnd and self.icon_path.endswith('.ico'):
                    try:
                        # Load icon with different sizes
                        icon_path = os.path.abspath(self.icon_path)
                        
                        # Load small icon (16x16) for taskbar
                        hicon_small = ctypes.windll.user32.LoadImageW(
                            0, icon_path, 1, 16, 16, 0x00000050  # LR_LOADFROMFILE | LR_DEFAULTSIZE
                        )
                        
                        # Load large icon (32x32) for window
                        hicon_large = ctypes.windll.user32.LoadImageW(
                            0, icon_path, 1, 32, 32, 0x00000050  # LR_LOADFROMFILE | LR_DEFAULTSIZE
                        )
                        
                        if hicon_small:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon_small)  # WM_SETICON, ICON_SMALL
                            
                        if hicon_large:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon_large)  # WM_SETICON, ICON_BIG
                        
                        # Force window to redraw
                        ctypes.windll.user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0004)  # RDW_INVALIDATE | RDW_UPDATENOW
                        
                        debug_log(f"Forced taskbar icon update for hwnd: {hwnd}")
                        
                    except Exception as e:
                        debug_log(f"Error in force_taskbar_icon: {e}")
                        
        except Exception as e:
            debug_log(f"Error forcing taskbar icon: {e}")
    
    def ensure_taskbar_icon(self):
        """Ensure taskbar icon is properly set (compatibility method)"""
        self.force_taskbar_icon()
    
    def run(self):
        """Start app"""
        # Test FFmpeg on startup
        self.test_ffmpeg()
        
        # Initialize GPU detection
        self.initialize_gpu_acceleration()
        
        # Final icon check before main loop
        self.root.after(100, self.ensure_taskbar_icon)
        
        self.root.mainloop()
    
    def initialize_gpu_acceleration(self):
        """Initialize GPU acceleration and show status"""
        try:
            ffmpeg_cmd = self.get_ffmpeg_command()
            gpu_settings = get_gpu_settings(ffmpeg_cmd)
            
            if gpu_settings['gpu_type'] != 'cpu':
                status_msg = f"Ready - {gpu_settings['gpu_type'].upper()} GPU Acceleration Enabled"
                debug_log(f"GPU Acceleration: {gpu_settings['gpu_type'].upper()} ({gpu_settings['encoder']})")
                # Set permanent status showing GPU acceleration
                self.root.after(2000, lambda: self.set_permanent_status(status_msg))
            else:
                debug_log("GPU Acceleration: CPU only (no compatible GPU found)")
                # Keep standard ready status for CPU-only systems
                self.root.after(2000, lambda: self.set_permanent_status("Ready - CPU Processing"))
                
        except Exception as e:
            debug_log(f"GPU initialization error: {e}")

class SimpleDialog:
    """Simple option dialog"""
    
    def __init__(self, app_instance, title, options):
        self.app = app_instance
        self.dialog = ctk.CTkToplevel(app_instance.root)
        self.dialog.title(title)
        self.dialog.geometry("280x380")
        self.dialog.transient(app_instance.root)
        
        # Force dialog to stay on top
        self.dialog.attributes('-topmost', True)
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.grab_set()
        
        # Remove system title bar completely
        self.dialog.after(1, lambda: self.dialog.overrideredirect(True))
        
        # Set dialog icon immediately and with retries
        self.set_icon_immediate()
        self.dialog.after(1, self.set_icon_immediate)
        self.dialog.after(50, self.set_icon_immediate)
        self.dialog.after(150, self.set_icon_immediate)
        
        # Set initial position before removing title bar
        self.initial_geometry = "280x380"
        self.dialog.geometry(self.initial_geometry)
        
        # Center dialog relative to parent window
        self.center_dialog_on_parent(app_instance.root, title, options)
        
        # Additional enforcement to keep dialog on top
        self.dialog.after(100, self.ensure_on_top)
        self.dialog.after(500, self.ensure_on_top)
    
    def set_icon_immediate(self):
        """Set dialog icon using multiple aggressive methods"""
        try:
            # Get the main app's icon path - use self.app for SimpleDialog and CustomMergeDialog
            if hasattr(self, 'app') and hasattr(self.app, 'icon_path') and self.app.icon_path:
                icon_path = self.app.icon_path
            elif hasattr(self, 'parent') and hasattr(self.parent, 'icon_path') and self.parent.icon_path:
                icon_path = self.parent.icon_path
            else:
                # Use resource_path for compiled version
                ico_path = resource_path("icon.ico")
                png_path = resource_path("icon.png")
                if os.path.exists(ico_path):
                    icon_path = ico_path
                elif os.path.exists(png_path):
                    icon_path = png_path
                else:
                    icon_path = "icon.ico" if os.path.exists("icon.ico") else "icon.png"
            
            if not os.path.exists(icon_path):
                return
                
            # Method 1: Direct iconbitmap on dialog
            if icon_path.endswith('.ico'):
                self.dialog.iconbitmap(icon_path)
                # Also set on wm (window manager)
                self.dialog.wm_iconbitmap(icon_path)
            else:
                # Use PhotoImage for PNG
                if not hasattr(self, '_icon_image'):
                    self._icon_image = tk.PhotoImage(file=icon_path)
                self.dialog.iconphoto(True, self._icon_image)
                self.dialog.wm_iconphoto(True, self._icon_image)
            
            # Method 2: Windows-specific approach
            if sys.platform == 'win32':
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # Try to get window handle from the dialog widget
                    try:
                        # Get the window ID from tkinter
                        hwnd = self.dialog.winfo_id()
                        # Get the actual window handle
                        hwnd = ctypes.windll.user32.GetParent(hwnd)
                        if not hwnd:
                            hwnd = self.dialog.winfo_id()
                    except:
                        # Fallback: Find by window title
                        hwnd = ctypes.windll.user32.FindWindowW(None, self.dialog.title())
                    
                    if hwnd and icon_path.endswith('.ico'):
                        # Load icon and set it
                        icon_flags = 0x00000000  # LR_DEFAULTCOLOR
                        hicon = ctypes.windll.user32.LoadImageW(
                            0, os.path.abspath(icon_path), 1, 0, 0, 0x00000010 | icon_flags  # IMAGE_ICON | LR_LOADFROMFILE
                        )
                        if hicon:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)  # WM_SETICON, ICON_SMALL
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)  # WM_SETICON, ICON_BIG
                            # Also set class icon
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, -14, hicon)  # GCL_HICON
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, -34, hicon)  # GCL_HICONSM
                except:
                    pass
            
        except Exception as e:
            debug_log(f"Error setting dialog icon: {e}")
    
    def center_dialog_on_parent(self, parent, title, options):
        """Center dialog on the parent window"""
        # Update parent to get correct position
        parent.update_idletasks()
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Adjusted dialog size for custom title bar and better tool options
        dialog_width = 280
        dialog_height = 380
        
        # Calculate center position relative to parent
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # Ensure dialog stays on screen
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        # Set geometry safely after overrideredirect
        try:
            geometry_string = f"{dialog_width}x{dialog_height}+{x}+{y}"
            self.dialog.after(10, lambda: self.safe_set_geometry(geometry_string))
        except:
            pass
        
        # Add custom title bar with icon
        self.add_custom_title_bar(title)
        
        # Setup dialog content
        self.setup_content(title, options)
    
    def setup_content(self, title, options):
        """Setup dialog content for tool options"""
        # Main content area with proper styling (no title since it's in custom title bar)
        content_area = ctk.CTkFrame(
            self.dialog, 
            fg_color="#34495e",  # Match main app background
            corner_radius=0
        )
        content_area.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Inner content with padding
        inner_content = ctk.CTkFrame(content_area, fg_color="transparent")
        inner_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Options with larger buttons for tool dialogs
        for text, command in options:
            ctk.CTkButton(
                inner_content, 
                text=text, 
                width=220, 
                height=40,
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="#0495ce",
                hover_color="#037ba3",
                text_color="#ffffff",
                command=lambda cmd=command: self.select(cmd)
            ).pack(pady=3)
        
        # Cancel button with different styling
        ctk.CTkButton(
            inner_content, 
            text="Cancel", 
            width=120, 
            height=35,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=["#7f8c8d", "#95a5a6"],
            hover_color=["#6c7b7d", "#85929e"],
            text_color="#ffffff",
            command=self.dialog.destroy
        ).pack(pady=(8, 0))
    
    def select(self, command):
        """Select option"""
        self.dialog.destroy()
        command()
    
    def setup_drag_functionality(self, title_frame):
        """Make dialog draggable by title bar"""
        def start_drag(event):
            self.dialog.x = event.x
            self.dialog.y = event.y
        
        def do_drag(event):
            x = self.dialog.winfo_pointerx() - self.dialog.x
            y = self.dialog.winfo_pointery() - self.dialog.y
            self.dialog.geometry(f"+{x}+{y}")
        
        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", do_drag)
        
        # Also bind to child widgets in title frame (except close button)
        for child in title_frame.winfo_children():
            for subchild in child.winfo_children():
                if "button" not in str(subchild).lower():
                    subchild.bind("<Button-1>", start_drag)
                    subchild.bind("<B1-Motion>", do_drag)
    
    def add_custom_title_bar(self, title):
        """Add custom title bar with icon and title for SimpleDialog"""
        try:
            # Load icon image using CTkImage for better scaling
            from PIL import Image
            icon_path = resource_path("icon.png")
            if not os.path.exists(icon_path):
                icon_path = "icon.png"  # Fallback for development
            icon_pil = Image.open(icon_path)
            self.title_icon = ctk.CTkImage(icon_pil, size=(25, 25))
        except:
            self.title_icon = None
        
        # Custom title bar frame with app theme
        title_frame = ctk.CTkFrame(
            self.dialog,
            height=45,
            fg_color="#0495ce",  # Match app blue theme
            corner_radius=0
        )
        title_frame.pack(fill="x", padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        # Content frame for icon and title
        content_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Icon label
        if self.title_icon:
            icon_label = ctk.CTkLabel(
                content_frame,
                image=self.title_icon,
                text="",
                width=25,
                height=25
            )
            icon_label.pack(side="left", padx=(0, 12))
        
        # Title label with tool dialog styling
        title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        title_label.pack(side="left")
        
        # Close button
        close_button = ctk.CTkButton(
            content_frame,
            text="×",
            width=25,
            height=25,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#d32f2f",
            border_color="#8B8B8B",
            border_width=1,
            hover_color="#d32f2f",
            text_color="white",
            command=self.dialog.destroy
        )
        close_button.pack(side="right")
        
        # Make title bar draggable
        self.setup_drag_functionality(title_frame)
    
    def safe_set_geometry(self, geometry_string):
        """Safely set dialog geometry after overrideredirect"""
        try:
            self.dialog.geometry(geometry_string)
        except:
            pass
    
    def ensure_on_top(self):
        """Ensure dialog stays on top and visible"""
        try:
            self.dialog.lift()
            self.dialog.attributes('-topmost', True)
            self.dialog.focus_force()
        except:
            pass

class CenteredMessageDialog:
    """Custom message dialog that's always centered on parent"""
    
    def __init__(self, parent, msg_type, title, message):
        self.parent = parent
        self.result = None
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Remove system title bar completely
        self.dialog.after(1, lambda: self.dialog.overrideredirect(True))
        
        # Set dialog icon immediately and with retries
        self.set_icon_immediate()
        self.dialog.after(1, self.set_icon_immediate)
        self.dialog.after(50, self.set_icon_immediate)
        self.dialog.after(150, self.set_icon_immediate)
        
        # Make dialog always stay on top and centered
        self.dialog.attributes('-topmost', True)
        
        # Add custom title bar with icon
        self.add_custom_title_bar(title)
        
        # Setup dialog content
        self.setup_dialog(msg_type, title, message)
        
        # Set initial position before removing title bar
        self.initial_geometry = "360x260"
        self.dialog.geometry(self.initial_geometry)
        
        # Center on parent
        self.center_on_parent()
        
        # Bind to parent window movement
        self.parent.bind('<Configure>', self.on_parent_move)
    
    def setup_dialog(self, msg_type, title, message):
        """Setup dialog content based on message type with beautiful design"""
        # Modern icons and colors for different message types
        dialog_config = {
            "info": {"icon": "ℹ", "color": "#3498db", "bg": "#2c3e50"},
            "warning": {"icon": "⚠", "color": "#f39c12", "bg": "#2c3e50"}, 
            "error": {"icon": "✕", "color": "#e74c3c", "bg": "#2c3e50"},
            "question": {"icon": "?", "color": "#9b59b6", "bg": "#2c3e50"}
        }
        
        config = dialog_config.get(msg_type, dialog_config["info"])
        
        # Set dialog background
        self.dialog.configure(fg_color=config["bg"])
        
        # Main container with elegant styling
        main_frame = ctk.CTkFrame(
            self.dialog,
            fg_color=config["bg"],
            border_color=config["color"],
            border_width=2,
            corner_radius=8
        )
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header with icon and subtle background
        header_frame = ctk.CTkFrame(
            main_frame,
            fg_color=config["color"],
            corner_radius=6,
            height=60
        )
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        header_frame.pack_propagate(False)
        
        # Icon in header
        ctk.CTkLabel(
            header_frame, 
            text=config["icon"], 
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="white"
        ).pack(expand=True)
        
        # Message with better typography and spacing
        message_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        message_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            message_frame, 
            text=message, 
            font=ctk.CTkFont(size=13, weight="normal"), 
            text_color="white",
            wraplength=280,
            justify="center"
        ).pack()
        
        # Enhanced buttons with rounded corners and hover effects
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 15))
        
        if msg_type in ["info", "warning", "error"]:
            ok_btn = ctk.CTkButton(
                button_frame, 
                text="OK", 
                width=120,
                height=35,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=config["color"],
                hover_color=self.get_hover_color(config["color"]),
                corner_radius=8,
                command=self.ok_clicked
            )
            ok_btn.pack()
        elif msg_type in ["question", "yesno"]:
            yes_btn = ctk.CTkButton(
                button_frame, 
                text="Yes", 
                width=90,
                height=35,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#27ae60",
                hover_color="#2ecc71",
                corner_radius=8,
                command=self.yes_clicked
            )
            yes_btn.pack(side="left", padx=(20, 10))
            
            no_btn = ctk.CTkButton(
                button_frame, 
                text="No", 
                width=90,
                height=35,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#c0392b",
                hover_color="#e74c3c",
                corner_radius=8,
                command=self.no_clicked
            )
            no_btn.pack(side="left", padx=(10, 20))
        
        # Larger dialog size for better appearance
        self.dialog.geometry("360x260")
    
    def get_hover_color(self, base_color):
        """Get a lighter hover color for buttons"""
        hover_colors = {
            "#3498db": "#5dade2",
            "#f39c12": "#f8c471", 
            "#e74c3c": "#ec7063",
            "#9b59b6": "#bb8fce"
        }
        return hover_colors.get(base_color, base_color)
    
    def center_on_parent(self):
        """Center dialog on parent window"""
        self.parent.update_idletasks()
        self.dialog.update_idletasks()
        
        # Get parent position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Get dialog size (updated for new design)
        dialog_width = 360
        dialog_height = 260
        
        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # Ensure dialog stays on screen
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        
        x = max(10, min(x, screen_width - dialog_width - 10))
        y = max(10, min(y, screen_height - dialog_height - 10))
        
        # Set geometry safely after overrideredirect
        try:
            geometry_string = f"{dialog_width}x{dialog_height}+{x}+{y}"
            self.dialog.after(10, lambda: self.safe_set_geometry(geometry_string))
        except:
            pass
    
    def on_parent_move(self, event):
        """Re-center dialog when parent moves"""
        if event.widget == self.parent:
            self.dialog.after_idle(self.center_on_parent)
    
    def ok_clicked(self):
        self.result = True
        self.cleanup()
    
    def yes_clicked(self):
        self.result = True
        self.cleanup()
    
    def no_clicked(self):
        self.result = False
        self.cleanup()
    
    def set_icon_immediate(self):
        """Set dialog icon using multiple aggressive methods"""
        try:
            # Get the main app's icon path - use self.app for SimpleDialog and CustomMergeDialog
            if hasattr(self, 'app') and hasattr(self.app, 'icon_path') and self.app.icon_path:
                icon_path = self.app.icon_path
            elif hasattr(self, 'parent') and hasattr(self.parent, 'icon_path') and self.parent.icon_path:
                icon_path = self.parent.icon_path
            else:
                # Use resource_path for compiled version
                ico_path = resource_path("icon.ico")
                png_path = resource_path("icon.png")
                if os.path.exists(ico_path):
                    icon_path = ico_path
                elif os.path.exists(png_path):
                    icon_path = png_path
                else:
                    icon_path = "icon.ico" if os.path.exists("icon.ico") else "icon.png"
            
            if not os.path.exists(icon_path):
                return
                
            # Method 1: Direct iconbitmap on dialog
            if icon_path.endswith('.ico'):
                self.dialog.iconbitmap(icon_path)
                # Also set on wm (window manager)
                self.dialog.wm_iconbitmap(icon_path)
            else:
                # Use PhotoImage for PNG
                if not hasattr(self, '_icon_image'):
                    self._icon_image = tk.PhotoImage(file=icon_path)
                self.dialog.iconphoto(True, self._icon_image)
                self.dialog.wm_iconphoto(True, self._icon_image)
            
            # Method 2: Windows-specific approach
            if sys.platform == 'win32':
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # Try to get window handle from the dialog widget
                    try:
                        # Get the window ID from tkinter
                        hwnd = self.dialog.winfo_id()
                        # Get the actual window handle
                        hwnd = ctypes.windll.user32.GetParent(hwnd)
                        if not hwnd:
                            hwnd = self.dialog.winfo_id()
                    except:
                        # Fallback: Find by window title
                        hwnd = ctypes.windll.user32.FindWindowW(None, self.dialog.title())
                    
                    if hwnd and icon_path.endswith('.ico'):
                        # Load icon and set it
                        icon_flags = 0x00000000  # LR_DEFAULTCOLOR
                        hicon = ctypes.windll.user32.LoadImageW(
                            0, os.path.abspath(icon_path), 1, 0, 0, 0x00000010 | icon_flags  # IMAGE_ICON | LR_LOADFROMFILE
                        )
                        if hicon:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)  # WM_SETICON, ICON_SMALL
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)  # WM_SETICON, ICON_BIG
                            # Also set class icon
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, -14, hicon)  # GCL_HICON
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, -34, hicon)  # GCL_HICONSM
                except:
                    pass
            
        except Exception as e:
            debug_log(f"Error setting dialog icon: {e}")
    
    def add_custom_title_bar(self, title):
        """Add custom title bar with icon and title for CenteredMessageDialog"""
        try:
            # Load icon image for message dialogs using CTkImage for better scaling
            from PIL import Image
            icon_pil = Image.open("icon.png")
            self.title_icon = ctk.CTkImage(icon_pil, size=(20, 20))
        except:
            self.title_icon = None
        
        # Custom title bar frame with app theme
        title_frame = ctk.CTkFrame(
            self.dialog,
            height=40,
            fg_color="#0495ce",  # Match app blue theme
            corner_radius=0
        )
        title_frame.pack(fill="x", padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        # Content frame for icon and title
        content_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=12, pady=8)
        
        # Icon label
        if self.title_icon:
            icon_label = ctk.CTkLabel(
                content_frame,
                image=self.title_icon,
                text="",
                width=20,
                height=20
            )
            icon_label.pack(side="left", padx=(0, 10))
        
        # Title label with message dialog styling
        title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        title_label.pack(side="left")
        
        # Close button
        close_button = ctk.CTkButton(
            content_frame,
            text="×",
            width=25,
            height=25,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#d32f2f",
            border_color="#8B8B8B",
            border_width=1,
            hover_color="#d32f2f",
            text_color="white",
            command=self.dialog.destroy
        )
        close_button.pack(side="right")
        
        # Make title bar draggable
        self.setup_drag_functionality(title_frame)
    
    def safe_set_geometry(self, geometry_string):
        """Safely set dialog geometry after overrideredirect"""
        try:
            self.dialog.geometry(geometry_string)
        except:
            pass
    
    def cleanup(self):
        """Cleanup dialog"""
        self.parent.unbind('<Configure>')
        self.dialog.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.dialog.wait_window()
        return self.result
    
    def setup_drag_functionality(self, title_frame):
        """Make dialog draggable by title bar"""
        def start_drag(event):
            self.dialog.x = event.x
            self.dialog.y = event.y
        
        def do_drag(event):
            x = self.dialog.winfo_pointerx() - self.dialog.x
            y = self.dialog.winfo_pointery() - self.dialog.y
            self.dialog.geometry(f"+{x}+{y}")
        
        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", do_drag)
        
        # Also bind to child widgets in title frame (except close button)
        for child in title_frame.winfo_children():
            for subchild in child.winfo_children():
                if "button" not in str(subchild).lower():
                    subchild.bind("<Button-1>", start_drag)
                    subchild.bind("<B1-Motion>", do_drag)

class CustomMergeDialog:
    """Custom dialog for merge settings with textbox input"""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.dialog = ctk.CTkToplevel(app_instance.root)
        self.dialog.title("🔀 Custom Merge")
        self.dialog.geometry("320x340")
        self.dialog.transient(app_instance.root)
        
        # Force dialog to stay on top
        self.dialog.attributes('-topmost', True)
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.grab_set()
        
        # Remove system title bar completely
        self.dialog.after(1, lambda: self.dialog.overrideredirect(True))
        
        # Set dialog icon immediately and with retries
        self.set_icon_immediate()
        self.dialog.after(1, self.set_icon_immediate)
        self.dialog.after(50, self.set_icon_immediate)
        self.dialog.after(150, self.set_icon_immediate)
        
        # Add custom title bar with icon
        self.add_custom_title_bar("🔀 Custom Merge")
        
        # Set initial position before removing title bar
        self.initial_geometry = "320x340"
        self.dialog.geometry(self.initial_geometry)
        
        # Center dialog relative to parent window
        self.center_dialog_on_parent()
        self.setup_content()
    
    def set_icon_immediate(self):
        """Set dialog icon using multiple aggressive methods"""
        try:
            # Get the main app's icon path - use self.app for SimpleDialog and CustomMergeDialog
            if hasattr(self, 'app') and hasattr(self.app, 'icon_path') and self.app.icon_path:
                icon_path = self.app.icon_path
            elif hasattr(self, 'parent') and hasattr(self.parent, 'icon_path') and self.parent.icon_path:
                icon_path = self.parent.icon_path
            else:
                # Use resource_path for compiled version
                ico_path = resource_path("icon.ico")
                png_path = resource_path("icon.png")
                if os.path.exists(ico_path):
                    icon_path = ico_path
                elif os.path.exists(png_path):
                    icon_path = png_path
                else:
                    icon_path = "icon.ico" if os.path.exists("icon.ico") else "icon.png"
            
            if not os.path.exists(icon_path):
                return
                
            # Method 1: Direct iconbitmap on dialog
            if icon_path.endswith('.ico'):
                self.dialog.iconbitmap(icon_path)
                # Also set on wm (window manager)
                self.dialog.wm_iconbitmap(icon_path)
            else:
                # Use PhotoImage for PNG
                if not hasattr(self, '_icon_image'):
                    self._icon_image = tk.PhotoImage(file=icon_path)
                self.dialog.iconphoto(True, self._icon_image)
                self.dialog.wm_iconphoto(True, self._icon_image)
            
            # Method 2: Windows-specific approach
            if sys.platform == 'win32':
                try:
                    import ctypes
                    from ctypes import wintypes
                    
                    # Try to get window handle from the dialog widget
                    try:
                        # Get the window ID from tkinter
                        hwnd = self.dialog.winfo_id()
                        # Get the actual window handle
                        hwnd = ctypes.windll.user32.GetParent(hwnd)
                        if not hwnd:
                            hwnd = self.dialog.winfo_id()
                    except:
                        # Fallback: Find by window title
                        hwnd = ctypes.windll.user32.FindWindowW(None, self.dialog.title())
                    
                    if hwnd and icon_path.endswith('.ico'):
                        # Load icon and set it
                        icon_flags = 0x00000000  # LR_DEFAULTCOLOR
                        hicon = ctypes.windll.user32.LoadImageW(
                            0, os.path.abspath(icon_path), 1, 0, 0, 0x00000010 | icon_flags  # IMAGE_ICON | LR_LOADFROMFILE
                        )
                        if hicon:
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)  # WM_SETICON, ICON_SMALL
                            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)  # WM_SETICON, ICON_BIG
                            # Also set class icon
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, -14, hicon)  # GCL_HICON
                            ctypes.windll.user32.SetClassLongPtrW(hwnd, -34, hicon)  # GCL_HICONSM
                except:
                    pass
            
        except Exception as e:
            debug_log(f"Error setting dialog icon: {e}")
    
    def center_dialog_on_parent(self):
        """Center dialog on the parent window"""
        # Update parent to get correct position
        self.app.root.update_idletasks()
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.app.root.winfo_x()
        parent_y = self.app.root.winfo_y()
        parent_width = self.app.root.winfo_width()
        parent_height = self.app.root.winfo_height()
        
        # Get dialog size
        dialog_width = 300
        dialog_height = 300
        
        # Calculate center position relative to parent
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # Ensure dialog stays on screen
        screen_width = self.app.root.winfo_screenwidth()
        screen_height = self.app.root.winfo_screenheight()
        
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        # Set geometry safely after overrideredirect
        try:
            geometry_string = f"{dialog_width}x{dialog_height}+{x}+{y}"
            self.dialog.after(10, lambda: self.safe_set_geometry(geometry_string))
        except:
            pass
    
    def setup_content(self):
        """Setup dialog content"""
        # Main content area (title now in custom title bar)
        content_area = ctk.CTkFrame(
            self.dialog, 
            fg_color="#34495e",  # Match main app background
            corner_radius=0
        )
        content_area.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Inner content with padding
        inner_content = ctk.CTkFrame(content_area, fg_color="transparent")
        inner_content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Description
        total_videos = len(self.app.videos)
        description = f"Total videos: {total_videos}\nSpecify how many videos per merge group:"
        ctk.CTkLabel(inner_content, text=description, 
                    font=ctk.CTkFont(size=12),
                    text_color=["#333333", "#ffffff"]).pack(pady=(0, 15))
        
        # Input frame
        input_frame = ctk.CTkFrame(inner_content, fg_color="transparent")
        input_frame.pack(pady=10)
        
        ctk.CTkLabel(input_frame, text="Videos per group:", 
                    font=ctk.CTkFont(size=12),
                    text_color=["#333333", "#ffffff"]).pack()
        
        self.video_count_entry = ctk.CTkEntry(input_frame, width=80, 
                                            placeholder_text="e.g. 3")
        self.video_count_entry.pack(pady=5)
        self.video_count_entry.focus()
        
        # Example text
        example_text = f"Example: Enter '3' to merge every 3 videos\ninto separate output files"
        ctk.CTkLabel(inner_content, text=example_text, 
                    font=ctk.CTkFont(size=10), 
                    text_color=["#7f8c8d", "#95a5a6"]).pack(pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(inner_content, fg_color="transparent")
        button_frame.pack(pady=15)
        
        ctk.CTkButton(button_frame, text="Start Merge", width=100,
                     fg_color="#0495ce",
                     hover_color="#037ba3",
                     text_color="#ffffff",
                     command=self.start_merge).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Cancel", width=80,
                     fg_color=["#7f8c8d", "#95a5a6"],
                     hover_color=["#6c7b7d", "#85929e"],
                     text_color="#ffffff",
                     command=self.dialog.destroy).pack(side="left", padx=5)
        
        # Bind Enter key to start merge
        self.video_count_entry.bind("<Return>", lambda event: self.start_merge())
    
    def setup_drag_functionality(self, title_frame):
        """Make dialog draggable by title bar"""
        def start_drag(event):
            self.dialog.x = event.x
            self.dialog.y = event.y
        
        def do_drag(event):
            x = self.dialog.winfo_pointerx() - self.dialog.x
            y = self.dialog.winfo_pointery() - self.dialog.y
            self.dialog.geometry(f"+{x}+{y}")
        
        title_frame.bind("<Button-1>", start_drag)
        title_frame.bind("<B1-Motion>", do_drag)
        
        # Also bind to child widgets in title frame (except close button)
        for child in title_frame.winfo_children():
            for subchild in child.winfo_children():
                if "button" not in str(subchild).lower():
                    subchild.bind("<Button-1>", start_drag)
                    subchild.bind("<B1-Motion>", do_drag)
    
    def start_merge(self):
        """Start custom merge process"""
        try:
            video_count = int(self.video_count_entry.get().strip())
            if video_count <= 0:
                raise ValueError("Must be positive")
            
            if video_count > len(self.app.videos):
                self.app.show_centered_message("warning", "Too Many Videos", 
                    f"You only have {len(self.app.videos)} videos.\nPlease enter a smaller number.")
                return
            
            self.dialog.destroy()
            self.app.process("merge_custom", video_count)
            
        except ValueError:
            self.app.show_centered_message("error", "Invalid Input", 
                "Please enter a valid positive number.")
    
    def add_custom_title_bar(self, title):
        """Add custom title bar with icon and title for CustomMergeDialog"""
        try:
            # Load icon image using CTkImage for better scaling
            from PIL import Image
            icon_path = resource_path("icon.png")
            if not os.path.exists(icon_path):
                icon_path = "icon.png"  # Fallback for development
            icon_pil = Image.open(icon_path)
            self.title_icon = ctk.CTkImage(icon_pil, size=(20, 20))
        except:
            self.title_icon = None
        
        # Custom title bar frame with app theme
        title_frame = ctk.CTkFrame(
            self.dialog,
            height=40,
            fg_color="#0495ce",  # Match app blue theme
            corner_radius=0
        )
        title_frame.pack(fill="x", padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        # Content frame for icon and title
        content_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=12, pady=8)
        
        # Icon label
        if self.title_icon:
            icon_label = ctk.CTkLabel(
                content_frame,
                image=self.title_icon,
                text="",
                width=20,
                height=20
            )
            icon_label.pack(side="left", padx=(0, 10))
        
        # Title label with message dialog styling
        title_label = ctk.CTkLabel(
            content_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        title_label.pack(side="left")
        
        # Close button
        close_button = ctk.CTkButton(
            content_frame,
            text="×",
            width=25,
            height=25,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="transparent",
            hover_color="#d32f2f",
            text_color="white",
            command=self.dialog.destroy
        )
        close_button.pack(side="right")
        
        # Make title bar draggable
        self.setup_drag_functionality(title_frame)
    
    def safe_set_geometry(self, geometry_string):
        """Safely set dialog geometry after overrideredirect"""
        try:
            self.dialog.geometry(geometry_string)
        except:
            pass

def main():
    try:
        app = CutPro()
        app.run()
    except Exception as e:
        # In compiled version, show error dialog instead of console output
        if getattr(sys, 'frozen', False):
            try:
                import tkinter.messagebox as mb
                mb.showerror("Error", f"Application error: {str(e)}")
            except:
                pass
        else:
            # In development, still show console errors
            raise e


class FFmpegDownloadDialog:
    """Dialog for downloading FFmpeg with progress"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        self.dialog = None
        self.progress_label = None
        self.progress_bar = None
        self.is_downloading = False
        self.download_cancelled = False
        # Get icon path from parent
        self.icon_path = self.get_icon_path()
    
    def get_icon_path(self):
        """Get icon path for the dialog"""
        # Try to get from parent if available
        if hasattr(self.parent, 'icon_path'):
            return self.parent.icon_path
        
        # Fallback to resource_path
        ico_path = resource_path("icon.ico")
        png_path = resource_path("icon.png")
        
        if os.path.exists(ico_path):
            return ico_path
        elif os.path.exists(png_path):
            return png_path
        
        # Fallback to local paths
        if os.path.exists("icon.ico"):
            return "icon.ico"
        elif os.path.exists("icon.png"):
            return "icon.png"
        
        return None
    
    def set_dialog_icon(self):
        """Set dialog icon"""
        if not self.icon_path or not self.dialog:
            return
            
        try:
            if self.icon_path.endswith('.ico'):
                self.dialog.iconbitmap(self.icon_path)
                self.dialog.wm_iconbitmap(self.icon_path)
            else:
                # For PNG files, convert to PhotoImage
                if not hasattr(self, '_dialog_icon_image'):
                    import tkinter as tk
                    self._dialog_icon_image = tk.PhotoImage(file=self.icon_path)
                self.dialog.iconphoto(True, self._dialog_icon_image)
                self.dialog.wm_iconphoto(True, self._dialog_icon_image)
                
        except Exception as e:
            debug_log(f"Error setting download dialog icon: {e}")
    
    def download_ffmpeg(self):
        """Show dialog and download FFmpeg"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("FFmpeg Setup")
        self.dialog.geometry("400x200")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Set dialog icon
        self.set_dialog_icon()
        
        # Aggressive stay-on-top configuration
        self.dialog.attributes('-topmost', True)
        self.dialog.lift()
        self.dialog.focus_force()
        
        # Ensure dialog stays above parent even with overrideredirect
        def keep_on_top():
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.attributes('-topmost', True)
                    self.dialog.lift()
                    # Schedule next check
                    self.dialog.after(500, keep_on_top)
            except:
                pass
        
        # Remove system title bar after ensuring position
        def setup_override():
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.overrideredirect(True)
                    # Re-center and ensure on top after override
                    self.center_dialog()
                    self.dialog.attributes('-topmost', True)
                    self.dialog.lift()
                    # Start periodic keep-on-top check
                    keep_on_top()
            except:
                pass
        
        self.dialog.after(50, setup_override)
        
        # Content frame
        content_frame = ctk.CTkFrame(self.dialog, fg_color="#34495e")
        content_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Custom title bar
        title_frame = ctk.CTkFrame(content_frame, fg_color="#0495ce", height=40)
        title_frame.pack(fill="x", padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        # Title label (left side)
        ctk.CTkLabel(
            title_frame,
            text="⬇️ Cut Pro Setup Required",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        ).pack(side="left", padx=15, pady=10)
        
        # Close button (right side)
        close_btn = ctk.CTkButton(
            title_frame,
            text="×",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white",
            fg_color="transparent",
            hover_color="#c0392b",
            width=30,
            height=30,
            command=self.cancel_download
        )
        close_btn.pack(side="right", padx=10, pady=5)
        
        # Message
        message_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        message_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            message_frame,
            text="Cut Pro needs FFmpeg for video processing.\nDownloading and installing FFmpeg automatically...",
            font=ctk.CTkFont(size=12),
            text_color="white",
            justify="center"
        ).pack(pady=(0, 15))
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            message_frame,
            text="Preparing download...",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.progress_label.pack(pady=5)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(message_frame, width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # Cancel button
        button_frame = ctk.CTkFrame(message_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#7f8c8d",
            hover_color="#6c7b7d",
            command=self.cancel_download
        )
        self.cancel_btn.pack(anchor="center")
        
        # Center dialog
        self.center_dialog()
        
        # Track parent movement to keep dialog positioned
        def track_parent_movement():
            try:
                if self.dialog and self.dialog.winfo_exists() and self.parent.winfo_exists():
                    # Re-center if parent moved significantly
                    current_parent_x = self.parent.winfo_x()
                    current_parent_y = self.parent.winfo_y()
                    if not hasattr(self, '_last_parent_pos'):
                        self._last_parent_pos = (current_parent_x, current_parent_y)
                    
                    last_x, last_y = self._last_parent_pos
                    if abs(current_parent_x - last_x) > 10 or abs(current_parent_y - last_y) > 10:
                        self.center_dialog()
                        self._last_parent_pos = (current_parent_x, current_parent_y)
                    
                    # Schedule next check
                    self.dialog.after(200, track_parent_movement)
            except:
                pass
        
        # Start tracking after dialog is set up
        self.dialog.after(100, track_parent_movement)
        
        # Auto-start download after a brief delay
        self.dialog.after(1000, self.start_download)
        
        # Wait for result
        self.dialog.wait_window()
        return self.result
    
    def center_dialog(self):
        """Center dialog on parent window with aggressive positioning"""
        try:
            self.dialog.update_idletasks()
            self.parent.update_idletasks()
            
            # Get parent window position and size
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # Dialog dimensions
            dialog_width = 400
            dialog_height = 200
            
            # Calculate perfect center position relative to parent
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            # Ensure dialog stays on screen
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            
            x = max(10, min(x, screen_width - dialog_width - 10))
            y = max(10, min(y, screen_height - dialog_height - 10))
            
            # Aggressively set geometry and ensure on top
            geometry = f"{dialog_width}x{dialog_height}+{x}+{y}"
            self.dialog.geometry(geometry)
            
            # Multiple methods to ensure it stays on top
            self.dialog.attributes('-topmost', True)
            self.dialog.lift()
            self.dialog.focus_force()
            self.dialog.grab_set()
            
            # Force parent to background temporarily to ensure dialog visibility
            self.parent.attributes('-topmost', False)
            self.dialog.after(100, lambda: self.parent.attributes('-topmost', False))
            
            debug_log(f"Dialog centered at {geometry} relative to parent")
            
        except Exception as e:
            debug_log(f"Error centering dialog: {e}")
            # Fallback to screen center with aggressive positioning
            screen_width = self.dialog.winfo_screenwidth() 
            screen_height = self.dialog.winfo_screenheight()
            x = (screen_width - 400) // 2
            y = (screen_height - 200) // 2
            self.dialog.geometry(f"400x200+{x}+{y}")
            self.dialog.attributes('-topmost', True)
            self.dialog.lift()
            self.dialog.focus_force()
    
    def start_download(self):
        """Start FFmpeg download in background thread"""
        if self.is_downloading:
            return  # Prevent multiple downloads
        
        self.is_downloading = True
        self.download_cancelled = False
        self.progress_label.configure(text="Connecting to server...")
        self.progress_bar.set(0)
        
        # Disable retry button if it exists
        if hasattr(self, 'retry_btn'):
            self.retry_btn.configure(state="disabled")
        
        threading.Thread(target=self.download_worker, daemon=True).start()
    
    def download_worker(self):
        """Download FFmpeg in background thread"""
        try:
            # Create a wrapper for progress callback that checks cancellation
            def progress_wrapper(msg):
                if not self.download_cancelled:
                    self.update_progress(msg)
                else:
                    raise Exception("Download cancelled")
            
            success = download_with_ultra_speed(progress_wrapper)
            if not self.download_cancelled:
                self.dialog.after(0, lambda: self.download_complete(success))
        except Exception as e:
            if not self.download_cancelled:
                self.dialog.after(0, lambda: self.download_failed(str(e)))
        finally:
            self.is_downloading = False
    
    def update_progress(self, message):
        """Update progress from background thread"""
        def update():
            if self.progress_label:
                self.progress_label.configure(text=message)
            if "%" in message and self.progress_bar:
                try:
                    # Extract percentage
                    percent = int(message.split('%')[0].split()[-1])
                    self.progress_bar.set(percent / 100.0)
                except:
                    pass
        
        if self.dialog:
            self.dialog.after(0, update)
    
    def download_complete(self, success):
        """Handle download completion"""
        if success:
            self.result = True
            self.progress_label.configure(text="FFmpeg installed successfully!")
            self.progress_bar.set(1.0)
            self.dialog.after(2000, self.dialog.destroy)  # Close after 2 seconds
        else:
            self.download_failed("Download failed")
    
    def download_failed(self, error):
        """Handle download failure"""
        self.is_downloading = False
        self.progress_label.configure(text=f"Error: {error[:50]}..." if len(error) > 50 else f"Error: {error}")
        self.progress_bar.set(0)
        
        # Hide cancel button
        self.cancel_btn.pack_forget()
        
        # Show retry button
        if not hasattr(self, 'retry_btn'):
            self.retry_btn = ctk.CTkButton(
                self.cancel_btn.master,  # Use same parent as cancel button
                text="Retry Download",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#e67e22",
                hover_color="#d35400",
                command=self.start_download
            )
        self.retry_btn.configure(state="normal")
        self.retry_btn.pack(anchor="center")
    
    def cancel_download(self):
        """Cancel download"""
        self.download_cancelled = True
        self.is_downloading = False
        self.result = False
        if self.dialog:
            self.dialog.destroy()


if __name__ == "__main__":
    main()