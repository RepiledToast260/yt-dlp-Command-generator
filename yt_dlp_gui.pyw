import os
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import threading
import platform
import time
import re
import json
import queue

# Constants
YT_DLP_EXECUTABLE = 'yt-dlp.exe'
ARIA2C_EXECUTABLE = 'aria2c.exe'
CONFIG_FILE = 'config.json'
URL_PATTERN = re.compile(r'^(https?://|www\.).+')
FORMAT_CODE_PATTERN = re.compile(r'^\d{2,3} \+ \d{2,3}$')

# Get the current working directory
current_dir = os.getcwd()
download_folder = "yt-dlp_Download"
download_path = os.path.join(current_dir, download_folder)

# Create the download directory if it doesn't exist
os.makedirs(download_path, exist_ok=True)

# Define paths to yt-dlp and aria2c
yt_dlp_path = os.path.join(current_dir, YT_DLP_EXECUTABLE)
aria2c_path = os.path.join(current_dir, ARIA2C_EXECUTABLE)

# Config file path
config_file_path = os.path.join(current_dir, CONFIG_FILE)

def load_config():
    """Load the download path from the config file if it exists."""
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as file:
            config = json.load(file)
            return config.get('download_path', download_path)
    return download_path

def save_config(download_path):
    """Save the download path to the config file."""
    with open(config_file_path, 'w') as file:
        json.dump({'download_path': download_path}, file)

# Default download path
default_download_path = load_config()

def validate_url(url):
    """Validate if the URL starts with 'http://', 'https://', or 'www.'."""
    return URL_PATTERN.match(url) is not None

def validate_number(number):
    """Check if the number is a valid positive integer."""
    return number.isdigit() and int(number) > 0

def validate_format_code(format_code):
    """Validate the custom format code to ensure it matches the pattern 'NNN + NNN'."""
    return FORMAT_CODE_PATTERN.match(format_code) is not None

def append_text(widget, text, clear=False):
    """Helper function to append text to a Text widget."""
    widget.config(state=tk.NORMAL)
    if clear:
        widget.delete(1.0, tk.END)
    widget.insert(tk.END, text)
    widget.config(state=tk.DISABLED)

def generate_command():
    video_url = url_entry.get().strip()
    download_path = download_path_entry.get().strip()
    start_number = start_entry.get().strip() if not start_checkbox_var.get() else "1"
    end_number = end_entry.get().strip()

    if not video_url:
        messagebox.showerror("Error", "Please enter a video URL.")
        return

    if not validate_url(video_url):
        messagebox.showerror("Error", "Invalid URL. The URL must start with 'http://', 'https://', or 'www.'.")
        return

    if not download_path:
        messagebox.showerror("Error", "Please enter a download path.")
        return

    if not start_checkbox_var.get() and not validate_number(start_number):
        messagebox.showerror("Error", "Please enter a valid starting number.")
        return

    if not end_checkbox_var.get() and not validate_number(end_number):
        messagebox.showerror("Error", "Please enter a valid ending number.")
        return

    custom_format_code = custom_format_entry.get().strip() if custom_format_var.get() else "bv+ba/b"

    if custom_format_var.get() and not validate_format_code(custom_format_code):
        messagebox.showerror("Error", "Invalid format code. Please use the format 'NNN + NNN'.")
        return

    # Construct command
    playlist_start_option = f'--playlist-start {start_number}' if start_number else ""
    playlist_end_option = f'--playlist-end {end_number}' if end_number else ""
    ext_downloader_option = f'--external-downloader "{aria2c_path}" ' if ext_downloader_var.get() else ""

    command = construct_command(video_url, download_path, playlist_start_option, playlist_end_option, ext_downloader_option, custom_format_code)
    
    append_text(result_text, command, clear=True)

def construct_command(video_url, download_path, playlist_start_option, playlist_end_option, ext_downloader_option, custom_format_code):
    """Construct the yt-dlp command based on user input."""
    if best_audio_var.get():
        command = (
            f'"{yt_dlp_path}" -P "{download_path}" '
            f'-f "ba/b" -x --audio-format wav '
            f'{ext_downloader_option} '
            f'{playlist_start_option} '
            f'{playlist_end_option} '
#            f'{custom_format_code} '  # Include custom format if provided
            f'-o "%(title)s.%(ext)s" "{video_url}"'
        )

    elif thumbnail_var.get():
        command = (
            f'"{yt_dlp_path}" -P "{download_path}" '
            f'--write-thumbnail --skip-download --convert-thumbnails png '
            f'{ext_downloader_option} '
            f'{playlist_start_option} '
            f'{playlist_end_option} '
#            f'{custom_format_code} '  # Include custom format if provided
            f'-o "%(title)s.%(ext)s" "{video_url}"'
        )

    else:
        command = (
            f'"{yt_dlp_path}" -P "{download_path}" '
            f'--embed-chapters --embed-metadata --embed-thumbnail '
            f'-f "{custom_format_code}" --merge-output-format mp4 '
            f'-S "vcodec:%%vcodec%%" -S "acodec:%%acodec%%" '
            f'{ext_downloader_option} '
            f'{playlist_start_option} '
            f'{playlist_end_option} '
#            f'{custom_format_code} '  # Include custom format if provided
            f'-o "%(title)s.%(ext)s" "{video_url}"'
        )
    return command

def copy_to_clipboard():
    command = result_text.get(1.0, tk.END).strip()
    if command:
        root.clipboard_clear()
        root.clipboard_append(command)
        messagebox.showinfo("Copied", "Command copied to clipboard!")

def run_command():
    command = result_text.get(1.0, tk.END).strip()
    if command:
        status_label.config(text="Running...")
        start_time = time.time()
        threading.Thread(target=update_timer, args=(start_time,), daemon=True).start()
        threading.Thread(target=execute_command, args=(command, start_time), daemon=True).start()

def execute_command(command, start_time):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for stdout_line in iter(process.stdout.readline, ""):
            append_text(output_text, stdout_line)
        process.stdout.close()
        process.wait()
    finally:
        status_label.config(text="Finished")

def update_timer(start_time):
    while status_label.cget("text") == "Running...":
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(int(elapsed_time), 60)
        timer_label.config(text=f"Elapsed Time: {minutes}m {seconds}s")
        time.sleep(1)

def open_default_path():
    try:
        if platform.system() == "Windows":
            os.startfile(download_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", download_path])
        else:
            subprocess.run(["xdg-open", download_path])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open folder: {e}")

def toggle_entry():
    if start_checkbox_var.get():
        start_entry.config(state='disabled')
        start_entry.delete(0, tk.END)
        start_entry.insert(0, "1")
    else:
        start_entry.config(state='normal')

def toggle_end_entry():
    if end_checkbox_var.get():
        end_entry.config(state='disabled')
        end_entry.delete(0, tk.END)
    else:
        end_entry.config(state='normal')

def change_download_path():
    new_path = download_path_entry.get().strip()
    if os.path.exists(new_path):
        save_config(new_path)
        messagebox.showinfo("Success", "Download path updated!")
    else:
        messagebox.showerror("Error", "The specified path does not exist.")

def reset_to_default_path():
    download_path_entry.config(state=tk.NORMAL)
    download_path_entry.delete(0, tk.END)
    download_path_entry.insert(0, default_download_path)
    download_path_entry.config(state="readonly")
    save_config(default_download_path)

def choose_folder():
    selected_folder = filedialog.askdirectory(initialdir=default_download_path)
    if selected_folder:
        download_path_entry.config(state=tk.NORMAL)
        download_path_entry.delete(0, tk.END)
        download_path_entry.insert(0, selected_folder)
        download_path_entry.config(state="readonly")
        save_config(selected_folder)

# Set up the main application window
root = tk.Tk()
root.title("yt-dlp Command Generator")

# Create and place the download path input field with button
path_frame = tk.Frame(root)
path_frame.pack(pady=5)

download_path_entry = tk.Entry(path_frame, width=50)
download_path_entry.pack(side=tk.LEFT, padx=(0, 5))
download_path_entry.insert(0, default_download_path)  # Set the default path
download_path_entry.config(state="readonly")  # Make it read-only but selectable

choose_folder_button = tk.Button(path_frame, text="Choose Download Folder", command=choose_folder)
choose_folder_button.pack(side=tk.LEFT)

# Create a frame for the reset and change path buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# Create and place the reset button inside the frame
reset_button = tk.Button(button_frame, text="Reset to Default Path", command=reset_to_default_path)
reset_button.pack(side=tk.LEFT, padx=5)

# Create and place the button to open the download folder
open_path_button = tk.Button(root, text="Open Download Folder", command=open_default_path)
open_path_button.pack(pady=5)

# Create and place the URL input field
tk.Label(root, text="Enter Video URL:").pack(pady=5)
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

# Create a frame for the checkbox and starting number
frame = tk.Frame(root)
frame.pack(pady=5)

# Create and place the checkbox for starting from the first video
start_checkbox_var = tk.BooleanVar(value=False)
start_checkbox = tk.Checkbutton(frame, text="Start playlist from first video", variable=start_checkbox_var, command=toggle_entry)
start_checkbox.pack(side=tk.LEFT)

# Create and place the entry for starting number
tk.Label(frame, text="Starting Number:").pack(side=tk.LEFT, padx=(10, 0))
start_entry = tk.Entry(frame, width=5)
start_entry.insert(0, "1")  # Default value
start_entry.pack(side=tk.LEFT)

# Create a frame for the checkbox and ending number
end_frame = tk.Frame(root)
end_frame.pack(pady=5)

# Create and place the checkbox for ending number
end_checkbox_var = tk.BooleanVar(value=True)  # Default to checked
end_checkbox = tk.Checkbutton(end_frame, text="End playlist at last video", variable=end_checkbox_var, command=toggle_end_entry)
end_checkbox.pack(side=tk.LEFT)

# Create and place the entry for ending number
tk.Label(end_frame, text="Ending Number:").pack(side=tk.LEFT, padx=(10, 0))
end_entry = tk.Entry(end_frame, width=5)
end_entry.insert(0, "")  # Default value empty
end_entry.pack(side=tk.LEFT)
end_entry.config(state='disabled')  # Initially disabled

# External downloader checkbox
ext_downloader_var = tk.BooleanVar(value=True)
ext_downloader_checkbox = tk.Checkbutton(root, text="External downloader (aria2c)", variable=ext_downloader_var)
ext_downloader_checkbox.pack(pady=5)

# Create and place the checkbox for best audio option
best_audio_var = tk.BooleanVar(value=False)
best_audio_checkbox = tk.Checkbutton(root, text="Audio Only (wav)", variable=best_audio_var)
best_audio_checkbox.pack(pady=5)

thumbnail_var = tk.BooleanVar(value=False)
thumbnail_checkbox = tk.Checkbutton(root, text="thumbnail Only", variable=thumbnail_var)
thumbnail_checkbox.pack(pady=5)

# Custom format checkbox and entry
custom_format_var = tk.BooleanVar(value=False)
custom_format_checkbox = tk.Checkbutton(root, text="Use Custom Format", variable=custom_format_var)
custom_format_checkbox.pack(pady=5)

custom_format_entry = tk.Entry(root, width=30)
custom_format_entry.pack(pady=5)
custom_format_entry.config(state='disabled')  # Initially disabled

def toggle_custom_format_entry():
    if custom_format_var.get():
        custom_format_entry.config(state='normal')  # Enable the entry if checked
    else:
        custom_format_entry.config(state='disabled')  # Disable if unchecked

custom_format_checkbox.config(command=toggle_custom_format_entry)

# Create and place the generate button
generate_button = tk.Button(root, text="Generate Command", command=generate_command)
generate_button.pack(pady=5)

# Create and place the result Text widget
tk.Label(root, text="Command:").pack(pady=0)
result_text = tk.Text(root, width=70, height=10, wrap=tk.WORD)
result_text.pack(pady=5)
result_text.config(state=tk.DISABLED)  # Make it read-only initially

# Create and place the output Text widget for command output
tk.Label(root, text="Console:").pack(pady=0)
output_text = tk.Text(root, width=70, height=10, wrap=tk.WORD)
output_text.pack(pady=5)
output_text.config(state=tk.DISABLED)  # Make it read-only initially

# Create and place the copy button
copy_button = tk.Button(root, text="Copy to Clipboard", command=copy_to_clipboard)
copy_button.pack(pady=5)

# Create and place the run button
run_button = tk.Button(root, text="Run", command=run_command)
run_button.pack(pady=5)

# Create and place the status label
status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=0)

# Create and place the timer label
timer_label = tk.Label(root, text="Elapsed Time: 0s", fg="green")
timer_label.pack(pady=5)

# Run the application
root.mainloop()
