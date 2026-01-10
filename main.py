# Safe Boot Supervisor
import time
import machine
import os

print("Booting Supervisor...")
time.sleep(1)

def file_exists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

try:
    print("Starting App...")
    import app
except Exception as e:
    print("CRITICAL ERROR: App failed to start!")
    print(e)
    
    if file_exists("backup.py"):
        print("Restoring backup...")
        # Rename failed app to app_failed.py for debugging
        # overwrite if exists
        try:
            os.rename("app.py", "app_failed.py")
        except:
            pass # Maybe app.py didn't exist or other error, try to restore backup anyway
            
        os.rename("backup.py", "app.py")
        print("Backup restored. Rebooting...")
        time.sleep(2)
        machine.reset()
    else:
        print("No backup found. System halted.")
        # Optional: Blink LED rapidly to indicate failure
        led = machine.Pin("LED", machine.Pin.OUT)
        while True:
            led.toggle()
            time.sleep(0.1)
