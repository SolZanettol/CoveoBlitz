import asyncio
import websockets
import json
import sys
import os
import maps
import importlib

def importAppFromFolder(folder, module_name):
    sys.path.append(folder)
    importlib.invalidate_caches()
    module = importlib.import_module(module_name)
    sys.path.remove(folder)
    return module

appDev = importAppFromFolder('./Develop', 'application')

async def main(loop):
    bots = ['V4']
    n = len(bots) + 1
    delay = 10
    game_map = maps.qp[2]
    
    print('Running docker commands....')
    os.system(f'powershell docker container stop $(docker container ls -q)')
    os.system(f'docker run -d --rm -p 8765:8765 blitzmmxxi/play --nbOfCrews={n} --gameConfig={game_map} --delayBetweenTicksMs={delay}')
    print('Done!')

    await asyncio.sleep(1)
    tasks = []
    names = []
    tasks.append(loop.create_task(appDev.run('Develop')))
    for originalName in bots:
        name = originalName
        if name in names:
            name += f'_{len(names)}'
        names.append(originalName)
        folder = f'./Bots/{originalName}'
        module = importAppFromFolder(folder, originalName)
        tasks.append(loop.create_task(module.run(f'{name}')))

    while not all(map(lambda x: x.done(), tasks)):
        await asyncio.sleep(1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    

