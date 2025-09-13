"""
Example integration of auto-updater into your main Cut Pro application.
Add this code to your main auto.py file.
"""

import threading
import tkinter as tk
from tkinter import messagebox
import os
import sys
from updater import AutoUpdater

class UpdateManager:
    def __init__(self, main_app_instance=None):
        self.main_app = main_app_instance
        self.updater = AutoUpdater(current_version=self.get_current_version())
        self.update_check_on_startup = True

    def get_current_version(self):
        """Get current version from version.txt file"""
        try:
            if os.path.exists("version.txt"):
                with open("version.txt", 'r') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"Error reading version: {e}")
        return "1.0.0"  # Default version

    def check_for_updates_async(self, show_no_update_message=False):
        """Check for updates in background thread"""
        def check_updates():
            try:
                update_info = self.updater.check_for_updates()

                if update_info.get("error"):
                    if show_no_update_message:
                        messagebox.showerror("Update Error",
                                           f"Failed to check for updates:\n{update_info['error']}")
                    return

                if update_info.get("update_available"):
                    self.show_update_dialog(update_info)
                elif show_no_update_message:
                    messagebox.showinfo("No Updates", "You're using the latest version!")

            except Exception as e:
                if show_no_update_message:
                    messagebox.showerror("Update Error", f"An error occurred: {e}")

        thread = threading.Thread(target=check_updates, daemon=True)
        thread.start()

    def show_update_dialog(self, update_info):
        """Show update available dialog"""
        latest_version = update_info["latest_version"]
        release_notes = update_info.get("release_notes", "No release notes available.")

        message = f"Update Available!\n\n"
        message += f"Current Version: {self.updater.current_version}\n"
        message += f"Latest Version: {latest_version}\n\n"
        message += f"Release Notes:\n{release_notes[:300]}{'...' if len(release_notes) > 300 else ''}\n\n"
        message += "Would you like to download and install the update now?"

        result = messagebox.askyesno("Update Available", message)

        if result:
            self.perform_update_with_progress(update_info)

    def perform_update_with_progress(self, update_info):
        """Perform update with progress dialog"""
        # Create progress window
        progress_window = tk.Toplevel()
        progress_window.title("Updating Cut Pro...")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        progress_window.grab_set()  # Make it modal

        # Center the window
        progress_window.transient()
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (150 // 2)
        progress_window.geometry(f"400x150+{x}+{y}")

        # Progress label
        status_label = tk.Label(progress_window, text="Preparing update...", pady=10)
        status_label.pack()

        # Progress bar (simple text-based)
        progress_label = tk.Label(progress_window, text="0%", pady=5)
        progress_label.pack()

        def update_progress(progress, status_text="Downloading..."):
            status_label.config(text=status_text)
            progress_label.config(text=f"{progress:.1f}%")
            progress_window.update()

        def perform_update():
            try:
                # Find executable asset
                executable_asset = self.updater.find_executable_asset(
                    update_info.get("assets", [])
                )

                if not executable_asset:
                    raise Exception("Could not find executable in release assets")

                # Download with progress
                update_progress(0, "Downloading update...")

                def progress_callback(progress):
                    update_progress(progress, "Downloading update...")

                temp_file_path = self.updater.download_update(
                    executable_asset, progress_callback
                )

                if not temp_file_path:
                    raise Exception("Failed to download update")

                update_progress(100, "Installing update...")

                # Apply update
                target_path = os.path.join("dist", "CutPro.exe")
                if self.updater.apply_update(temp_file_path, target_path):
                    # Update version file
                    self.save_new_version(update_info["latest_version"])

                    progress_window.destroy()
                    messagebox.showinfo("Update Complete",
                                      "Update installed successfully!\n"
                                      "Please restart the application to use the new version.")

                    # Optionally restart the application
                    self.restart_application()
                else:
                    raise Exception("Failed to apply update")

            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Update Failed", f"Failed to update:\n{e}")

        # Start update in thread
        update_thread = threading.Thread(target=perform_update, daemon=True)
        update_thread.start()

    def save_new_version(self, new_version):
        """Save new version to version.txt"""
        try:
            with open("version.txt", 'w') as f:
                f.write(new_version)
        except Exception as e:
            print(f"Error saving new version: {e}")

    def restart_application(self):
        """Restart the application"""
        try:
            if messagebox.askyesno("Restart Application",
                                 "Do you want to restart the application now?"):
                # Close current instance
                if self.main_app and hasattr(self.main_app, 'root'):
                    self.main_app.root.quit()

                # Restart
                os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            print(f"Error restarting application: {e}")

    def add_update_menu_to_app(self, menu_bar):
        """Add update menu to your application's menu bar"""
        try:
            update_menu = tk.Menu(menu_bar, tearoff=0)
            update_menu.add_command(label="Check for Updates",
                                  command=lambda: self.check_for_updates_async(show_no_update_message=True))
            update_menu.add_separator()
            update_menu.add_command(label=f"Current Version: {self.get_current_version()}",
                                  state="disabled")

            menu_bar.add_cascade(label="Update", menu=update_menu)
        except Exception as e:
            print(f"Error adding update menu: {e}")


# Example integration in your main auto.py file:
"""
# In your main application class __init__ method:
self.update_manager = UpdateManager(main_app_instance=self)

# Add update menu to your menu bar:
self.update_manager.add_update_menu_to_app(your_menu_bar)

# Check for updates on startup (optional):
if hasattr(self, 'update_manager'):
    self.update_manager.check_for_updates_async()
"""

# Standalone test
if __name__ == "__main__":
    # Create a simple test window
    root = tk.Tk()
    root.title("Cut Pro Update Test")
    root.geometry("300x200")

    # Create menu bar
    menubar = tk.Menu(root)
    root.config(menu=menubar)

    # Initialize update manager
    update_mgr = UpdateManager()
    update_mgr.add_update_menu_to_app(menubar)

    # Add a test button
    test_button = tk.Button(root, text="Check for Updates",
                           command=lambda: update_mgr.check_for_updates_async(show_no_update_message=True))
    test_button.pack(pady=50)

    # Check for updates on startup
    root.after(1000, lambda: update_mgr.check_for_updates_async())

    root.mainloop()