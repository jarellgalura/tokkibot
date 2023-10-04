import threading
import subprocess


def run_script(script):
    subprocess.run(['python', script])


script1 = 'tiktok_bot.py'
script2 = 'twitter_bot.py'

thread1 = threading.Thread(target=run_script, args=(script1,))
thread2 = threading.Thread(target=run_script, args=(script2,))

thread1.start()
thread2.start()

thread1.join()
thread2.join()

print("All three scripts have finished running.")
