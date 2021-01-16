import asyncio
import websockets
import json
import sys
import os

sys.path.append('./Develop')
import application

if __name__ == "__main__":
    n = 2
    delay = 10
    game_map = '"2P-01.bmp"'
    
    print('Running docker commands....')
    os.system(f'powershell docker container stop $(docker container ls -q)')
    os.system(f'docker run -d --rm -p 8765:8765 blitzmmxxi/play --nbOfCrews={n} --game_config={game_map} --delayBetweenTicksMs={delay}')
    print('Done!')

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.sleep(1))
    tasks = []
    for i in range(n):
        tasks.append(loop.create_task(application.run(f'Develop-{i}')))

    while not all(map(lambda x: x.done(), tasks)):
        loop.run_until_complete(asyncio.sleep(1))

