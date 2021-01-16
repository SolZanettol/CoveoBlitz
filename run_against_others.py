import asyncio
import websockets
import json
import sys
import os
import maps
import importlib

def importAppFromFolder(folder):
    sys.path.append(folder)
    module = importlib.import_module('application')
    sys.path.remove(folder)
    return module

appDev = importAppFromFolder('./Develop')

async def main(loop):
    bots = ['Dev2']
    n = len(bots) + 1
    delay = 100
    game_map = maps.dp[0]
    
    print('Running docker commands....')
    os.system(f'powershell docker container stop $(docker container ls -q)')
    os.system(f'docker run -d --rm -p 8765:8765 blitzmmxxi/play --nbOfCrews={n} --gameConfig={game_map} --delayBetweenTicksMs={delay}')
    print('Done!')

    await asyncio.sleep(1)
    tasks = []
    tasks.append(loop.create_task(appDev.run('Develop')))
    for name in bots:
        folder = f'./Bots/{name}'
        module = importAppFromFolder(folder)
        tasks.append(loop.create_task(module.run(f'{name}')))

    while not all(map(lambda x: x.done(), tasks)):
        await asyncio.sleep(1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    

