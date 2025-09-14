import os
import psutil
from .base_skill import Skill

class SystemSkill(Skill):
    def intents(self):
        return ["battery", "notepad", "calculator"]

    def handle(self, command, doc):
        if "battery" in command:
            battery = psutil.sensors_battery()
            if not battery:
                return "I am unable to access battery information on this device.", "IDLE"
            
            percentage = battery.percent
            plugged = "plugged in" if battery.power_plugged else "not plugged in"
            return f"The system is at {percentage} percent battery and is currently {plugged}.", "IDLE"
        
        elif "notepad" in command or "calculator" in command:
            app = 'notepad' if 'notepad' in command else 'calc'
            app_name = "Notepad" if app == 'notepad' else "Calculator"
            try:
                os.system(f"start {app}") # This command is for Windows
                return f"Opening {app_name}...", "IDLE"
            except Exception as e:
                print(f"System skill error: {e}")
                return f"Sorry, I was unable to open {app_name}.", "IDLE"

        return "I can't perform that system action.", "IDLE"