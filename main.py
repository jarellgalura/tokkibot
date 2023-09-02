import subprocess

# Run script 1
process1 = subprocess.Popen(["python", "instagram_bot.py"])

# Run script 2
process2 = subprocess.Popen(["python", "kr_eng.py"])

# Wait for both scripts to finish
process1.wait()
process2.wait()
