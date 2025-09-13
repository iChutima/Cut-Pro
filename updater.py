import requests
import json
import os
import tempfile
import shutil
import subprocess
import sys
from packaging import version
from urllib.parse import urlparse

class AutoUpdater:
    def __init__(self, repo_owner="iChutima", repo_name="Cut-Pro", current_version="1.0.0"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.current_version = current_version
        self.api_base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.executable_name = "CutPro.exe"

    def check_for_updates(self):
        """Check if there's a newer version available"""
        try:
            # Get latest release from GitHub API
            response = requests.get(f"{self.api_base_url}/releases/latest", timeout=10)
            response.raise_for_status()

            release_data = response.json()
            latest_version = release_data["tag_name"].lstrip("v")  # Remove 'v' prefix if exists

            print(f"Current version: {self.current_version}")
            print(f"Latest version: {latest_version}")

            # Compare versions
            if version.parse(latest_version) > version.parse(self.current_version):
                return {
                    "update_available": True,
                    "latest_version": latest_version,
                    "release_notes": release_data.get("body", ""),
                    "release_url": release_data["html_url"],
                    "assets": release_data.get("assets", [])
                }
            else:
                return {"update_available": False}

        except requests.RequestException as e:
            print(f"Error checking for updates: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {"error": str(e)}

    def find_executable_asset(self, assets):
        """Find the executable file in release assets"""
        for asset in assets:
            if asset["name"] == self.executable_name:
                return asset
        return None

    def download_update(self, asset_info, progress_callback=None):
        """Download the update file"""
        try:
            download_url = asset_info["browser_download_url"]
            file_size = asset_info.get("size", 0)

            # Create temporary file
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, self.executable_name)

            print(f"Downloading update from: {download_url}")

            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            downloaded_size = 0
            with open(temp_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Call progress callback if provided
                        if progress_callback and file_size > 0:
                            progress = (downloaded_size / file_size) * 100
                            progress_callback(progress)

            print(f"Download completed: {temp_file_path}")
            return temp_file_path

        except Exception as e:
            print(f"Error downloading update: {e}")
            return None

    def backup_current_version(self, executable_path):
        """Create backup of current version"""
        try:
            backup_path = f"{executable_path}.backup"
            shutil.copy2(executable_path, backup_path)
            print(f"Backup created: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def apply_update(self, new_file_path, target_path):
        """Replace the current executable with the new one"""
        try:
            # Create backup first
            backup_path = self.backup_current_version(target_path)
            if not backup_path:
                return False

            # Replace the file
            shutil.move(new_file_path, target_path)
            print(f"Update applied successfully: {target_path}")

            # Clean up backup after successful update (optional)
            # os.remove(backup_path)

            return True

        except Exception as e:
            print(f"Error applying update: {e}")
            # Try to restore backup if something went wrong
            if backup_path and os.path.exists(backup_path):
                try:
                    shutil.move(backup_path, target_path)
                    print("Restored from backup due to error")
                except:
                    pass
            return False

    def perform_update(self, target_executable_path=None):
        """Complete update process"""
        if target_executable_path is None:
            target_executable_path = os.path.join("dist", self.executable_name)

        # Check for updates
        update_info = self.check_for_updates()

        if update_info.get("error"):
            print(f"Update check failed: {update_info['error']}")
            return False

        if not update_info.get("update_available"):
            print("No updates available")
            return True

        print(f"Update available: v{update_info['latest_version']}")
        if update_info.get("release_notes"):
            print(f"Release notes:\n{update_info['release_notes']}")

        # Find executable in assets
        executable_asset = self.find_executable_asset(update_info.get("assets", []))
        if not executable_asset:
            print(f"Could not find {self.executable_name} in release assets")
            return False

        # Download update
        def progress_callback(progress):
            print(f"Download progress: {progress:.1f}%")

        temp_file_path = self.download_update(executable_asset, progress_callback)
        if not temp_file_path:
            print("Failed to download update")
            return False

        # Apply update
        if self.apply_update(temp_file_path, target_executable_path):
            print("Update completed successfully!")
            print("Please restart the application to use the new version.")
            return True
        else:
            print("Failed to apply update")
            return False

    def get_current_version_from_file(self, version_file_path="version.txt"):
        """Read current version from a file"""
        try:
            if os.path.exists(version_file_path):
                with open(version_file_path, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Error reading version file: {e}")
        return self.current_version

    def save_version_to_file(self, version, version_file_path="version.txt"):
        """Save version to a file"""
        try:
            with open(version_file_path, 'w') as f:
                f.write(version)
        except Exception as e:
            print(f"Error saving version file: {e}")

# Example usage
if __name__ == "__main__":
    # Initialize updater
    updater = AutoUpdater(current_version="1.0.0")

    # Check for updates and perform if available
    if len(sys.argv) > 1 and sys.argv[1] == "--check-only":
        # Just check for updates
        update_info = updater.check_for_updates()
        if update_info.get("update_available"):
            print(f"Update available: v{update_info['latest_version']}")
        else:
            print("No updates available")
    else:
        # Perform full update
        updater.perform_update()