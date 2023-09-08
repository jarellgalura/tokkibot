import subprocess

# Run script 1
process1 = subprocess.Popen(["python", "hanni_bot.py"])

# Run script 2
process2 = subprocess.Popen(["python", "twitter_bot.py"])

# Wait for both scripts to finish
process1.wait()
process2.wait()
