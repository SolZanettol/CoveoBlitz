import asyncio
import websockets
import json
import sys
import os
import maps

sys.path.append('./Develop')
import application

async def main(loop):
    n = 2
    delay = 150
    game_map = maps.dp[12]
    ticks = 200
    
    print('Running docker commands....')
    os.system(f'powershell docker container stop $(docker container ls -q)')
    os.system(f'docker run -d --rm -p 8765:8765 blitzmmxxi/play --nbOfCrews={n} --gameConfig={game_map} --delayBetweenTicksMs={delay} --nbOfTicks={ticks}')
    print('Done!')

    await asyncio.sleep(1)
    tasks = []
    for i in range(n):
        tasks.append(loop.create_task(application.run(f'Develop-{i}')))

    while not all(map(lambda x: x.done(), tasks)):
        await asyncio.sleep(1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))