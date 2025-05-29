import os
import platform

def open_camera():
    system_name = platform.system()
    
    if system_name == "Windows":
        os.system("start microsoft.windows.camera:")  # Opens Windows Camera App
    elif system_name == "Darwin":  # macOS
        os.system("open -a FaceTime")  # Opens FaceTime (default camera app)
    elif system_name == "Linux":
        os.system("cheese")  # Opens Cheese (Linux default camera app)
    else:
        return "Unsupported OS"
    
    return "Camera opened!"
