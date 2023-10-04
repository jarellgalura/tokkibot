import asyncio


async def run_script(script):
    await asyncio.create_subprocess_exec('python', script)


async def main():
    script1 = 'instagram.py'
    script2 = 'tiktok_bot.py'
    script3 = 'twitter_bot.py'

    tasks = [
        run_script(script1),
        run_script(script2),
        run_script(script3),
    ]

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
    print("All three scripts have finished running.")
