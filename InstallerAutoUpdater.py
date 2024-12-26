import os
import sys
import json
import shutil
import subprocess
import requests
from datetime import datetime
from dulwich import porcelain
import atexit
import time

if hasattr(sys, '_MEIPASS'):
    temp_dir = sys._MEIPASS

    @atexit.register
    def cleanup_temp_dir():
        for _ in range(5):  # Retry cleanup up to 5 times
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"Successfully cleaned up temporary directory: {temp_dir}")
                break
            except Exception as e:
                print(f"Failed to clean up temporary directory {temp_dir}: {e}")
                time.sleep(1)  # Wait before retrying

class InstallerAutoUpdater:
    def __init__(self):
        self.base_path = os.path.join(os.environ['USERPROFILE'], 'OpenWebUI')
        self.config_file = os.path.join(self.base_path, 'config.json')
        self.exe_name = "InstallerAutoUpdater.exe"
        self.repo_url = "https://github.com/BrainDriveAI/OpenWebUI_CondaInstaller"
        self.release_url = "https://api.github.com/repos/BrainDriveAI/OpenWebUI_CondaInstaller/releases/latest"
        self.exe_path = os.path.join(self.base_path, self.exe_name)
        self.current_version = None
        self.load_config()

    def load_config(self):
        """Load or initialize the configuration file."""
        if not os.path.exists(self.config_file):
            self.initialize_config()
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        self.base_path = config['install_dir']
        self.current_version = config['current_version']

    def initialize_config(self):
        """Initialize the config file with default values."""
        os.makedirs(self.base_path, exist_ok=True)
        default_config = {
            "install_dir": self.base_path,
            "current_version": None,
            "last_checked": None,
        }
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=4)

    def save_config(self, key, value):
        """Save a key-value pair in the configuration."""
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        config[key] = value
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)

    def get_latest_release(self):
        """Fetch the latest release information from GitHub."""
        response = requests.get(self.release_url)
        response.raise_for_status()
        release_data = response.json()
        return release_data

    def download_file(self, url, dest_path):
        """Download a file from a URL to the specified destination."""
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
        except requests.ConnectionError:
            print("No internet connection. Unable to download the file.")
            return False
        except requests.Timeout:
            print("The download request timed out. Please try again.")
            return False
        except requests.RequestException as e:
            print(f"An error occurred while downloading the file: {e}")
            return False
        return True
    
    def check_and_update(self):
        """Check for updates and update if necessary."""
        latest_release = self.get_latest_release()
        if not latest_release:
            print("Update check failed. Please ensure you are connected to the internet.")
            return

        latest_version = latest_release['tag_name']
        download_url = next(
            (asset['browser_download_url'] for asset in latest_release['assets']
            if asset['name'] == "OpenWebUIInstaller.exe"), None
        )

        if not download_url:
            print("Failed to find the installer in the release assets.")
            return

        installer_path = os.path.join(self.base_path, "OpenWebUIInstaller.exe")

        if self.current_version == latest_version:
            self.save_config('last_checked', datetime.now().isoformat())
            print("You already have the latest version.")
            self.run_exe(installer_path)
        else:
            print(f"Downloading latest version ({latest_version})...")
            if self.download_file(download_url, installer_path):
                self.save_config('current_version', latest_version)
                self.save_config('last_checked', datetime.now().isoformat())
                self.run_exe(installer_path)
            else:
                print("Download failed. Please try again when you have a stable internet connection.")

    def run_exe(self, exe_path):
        """Run the specified executable from the correct location."""
        if not os.path.exists(exe_path):
            print(f"Error: The executable '{exe_path}' does not exist. Please ensure it has been downloaded successfully.")
            return

        try:
            print(f"Running {exe_path}...")
            subprocess.Popen([exe_path], cwd=self.base_path)
        except FileNotFoundError:
            print(f"Error: Unable to find the executable '{exe_path}'.")
        except PermissionError:
            print(f"Error: Permission denied while trying to run '{exe_path}'. Ensure you have the necessary permissions.")
        except subprocess.CalledProcessError as e:
            print(f"Executable returned an error: {e}")            
        except Exception as e:
            print(f"An unexpected error occurred while trying to run the executable: {e}")
        finally:
            # Ensure cleanup happens here
            if hasattr(sys, '_MEIPASS'):
                try:
                    shutil.rmtree(sys._MEIPASS, ignore_errors=True)
                except Exception as cleanup_err:
                    print(f"Failed to remove temporary directory: {cleanup_err}")
            sys.exit()


    def verify_install(self):
        """Verify the install directory and executable."""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
        if not os.path.exists(self.exe_path):
            shutil.copy2(sys.argv[0], self.exe_path)

    def main(self):
        """Main execution flow."""
        self.verify_install()
        self.check_and_update()


if __name__ == "__main__":
    try:
        updater = InstallerAutoUpdater()
        updater.main()
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
