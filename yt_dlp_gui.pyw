import os
import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import platform
import time
import re

# Get the current working directory
current_dir = os.getcwd()

# Define paths to yt-dlp and aria2c
yt_dlp_path = os.path.join(current_dir, 'yt-dlp.exe')
aria2c_path = os.path.join(current_dir, 'aria2c.exe')

# Default download path
default_download_path = "F:\\New_download"

def validate_url(url):
    """Validate if the URL starts with 'http://', 'https://', or 'www.'."""
    pattern = r'^(https?://|www\.).+'
    return re.match(pattern, url) is not None

def generate_command():
    video_url = url_entry.get().strip()
    download_path = download_path_entry.get().strip()
    start_number = start_entry.get().strip() if not start_checkbox_var.get() else "1"

    if not video_url:
        messagebox.showerror("Error", "Please enter a video URL.")
        return

    if not validate_url(video_url):
        messagebox.showerror("Error", "Invalid URL. The URL must start with 'http://', 'https://', or 'www.'.")
        return

    if not download_path:
        messagebox.showerror("Error", "Please enter a download path.")
        return

    # Check if the best audio option is selected
    if best_audio_var.get():
        command = (
            f'"{yt_dlp_path}" -P "{download_path}" '
            f'-f "ba/b" -x --audio-format wav '
#            f'-S "acodec:%%acodec%%" '
            f'--external-downloader "{aria2c_path}" '
            f'--playlist-start {start_number} '
            f'-o "%(title)s.%(ext)s" "{video_url}"'
            
        )
    else:
        command = (
            f'"{yt_dlp_path}" -P "{download_path}" '
            f'--embed-chapters --embed-metadata --embed-thumbnail '
            f'-f "bv+ba/b" --merge-output-format mp4 '
            f'-S "vcodec:%%vcodec%%" -S "acodec:%%acodec%%" '
            f'--external-downloader "{aria2c_path}" '
            f'--playlist-start {start_number} '
            f'-o "%(title)s.%(ext)s" "{video_url}"'
        )

    result_text.config(state=tk.NORMAL)  # Enable editing to insert text
    result_text.delete(1.0, tk.END)  # Clear previous content
    result_text.insert(tk.END, command)  # Insert the generated command
    result_text.config(state=tk.DISABLED)  # Make it read-only

def copy_to_clipboard():
    command = result_text.get(1.0, tk.END).strip()  # Get the command from the Text widget
    if command:
        root.clipboard_clear()  # Clear the clipboard
        root.clipboard_append(command)  # Append the command to the clipboard
        messagebox.showinfo("Copied", "Command copied to clipboard!")

def run_command():
    command = result_text.get(1.0, tk.END).strip()  # Get the command from the Text widget
    if command:
        status_label.config(text="Running...")  # Update status
        timer_label.config(text="Elapsed Time: 0s")  # Reset timer label
        start_time = time.time()  # Start the timer
        
        # Start the real-time timer update
        threading.Thread(target=update_timer, args=(start_time,)).start()
        
        # Run the command in a separate thread
        threading.Thread(target=execute_command, args=(command, start_time)).start()

def execute_command(command, start_time):
    try:
        # Run the shell command and capture output
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for stdout_line in iter(process.stdout.readline, ""):
            output_text.config(state=tk.NORMAL)
            output_text.insert(tk.END, stdout_line)  # Display command output
            output_text.config(state=tk.DISABLED)
            output_text.yview(tk.END)  # Scroll to the end
        process.stdout.close()
        process.wait()
    finally:
        # Once the command finishes, set the status to "Finished"
        status_label.config(text="Finished")

def update_timer(start_time):
    """Update the timer label every second with the elapsed time."""
    while status_label.cget("text") == "Running...":
        elapsed_time = time.time() - start_time
        minutes, seconds = divmod(int(elapsed_time), 60)
        timer_label.config(text=f"Elapsed Time: {minutes}m {seconds}s")
        time.sleep(1)  # Wait for 1 second before updating the timer again

def open_default_path():
    try:
        download_path = download_path_entry.get().strip()  # Get the current download path
        if platform.system() == "Windows":
            os.startfile(download_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", download_path])
        else:  # Linux and others
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

# Set up the main application window
root = tk.Tk()
root.title("yt-dlp Command Generator")

# Create and place the download path input field
tk.Label(root, text="Default Download Path:").pack(pady=5)
download_path_entry = tk.Entry(root, width=50)
download_path_entry.pack(pady=5)
download_path_entry.insert(0, default_download_path)  # Set the default path

# Create and place the button to open the default path
open_path_button = tk.Button(root, text="Open Download Folder", command=open_default_path)
open_path_button.pack(pady=10)

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

# Create and place the checkbox for best audio option
best_audio_var = tk.BooleanVar(value=False)
best_audio_checkbox = tk.Checkbutton(root, text="Download Best Audio (MP3)", variable=best_audio_var)
best_audio_checkbox.pack(pady=5)

# Create and place the generate button
generate_button = tk.Button(root, text="Generate Command", command=generate_command)
generate_button.pack(pady=10)

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
copy_button.pack(pady=10)

# Create and place the run button
run_button = tk.Button(root, text="Run", command=run_command)
run_button.pack(pady=10)

# Create and place the status label
status_label = tk.Label(root, text="", fg="blue")
status_label.pack(pady=5)

# Create and place the timer label
timer_label = tk.Label(root, text="Elapsed Time: 0s", fg="green")
timer_label.pack(pady=5)

# Run the application
root.mainloop()