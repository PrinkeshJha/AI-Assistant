import os
import psutil
from .base_skill import Skill

class SystemSkill(Skill):
    def intents(self):
        return ["battery", "notepad", "calculator"]

    def handle(self, command, doc):
        if "battery" in command:
            battery = psutil.sensors_battery()
            plugged_str = ""
            percentage = 100
            if battery:
                percentage = battery.percent
                plugged_str = f" and is currently {'plugged in' if battery.power_plugged else 'not plugged in'}"
            else:
                plugged_str = " (using AC power)"
                
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            return f"System metrics: Battery is at {percentage}%{plugged_str}. Server CPU usage is at {cpu}% and memory usage is at {memory}%.", "IDLE"
        
        elif "notepad" in command or "calculator" in command:
            app_name = "Notepad" if 'notepad' in command else "Calculator"
            return f"Opening {app_name} locally is disabled in Cloud Mode. However, the server stats show CPU at {psutil.cpu_percent()}% and memory at {psutil.virtual_memory().percent}%.", "IDLE"

        return "I can't perform that system action.", "IDLE"