import asyncio
import websockets
import json
import sys
import os

sys.path.append('./Develop')
import application

maps1p = "1P-01.bmp"

maps2p = [
    "2P-01.bmp",
    "2P-02.bmp",
    "2P-03.bmp",
    "2P-04.bmp",
    "2P-05.bmp",
    "2P-06.bmp",
    "2P-07.bmp",
    "2P-08.bmp",
    "2P-09.bmp",
    "2P-10.bmp",
    "2P-11.bmp",
    "2P-12.bmp",
    "2P-13.bmp",
    "2P-14.bmp",
    "2P-15.bmp",
    "2P-16.bmp"]
maps4p =[
    "4P-01.bmp",
    "4P-02.bmp",
    "4P-03.bmp",
    "4P-04.bmp",
    "4P-05.bmp",
    "4P-06.bmp",
    "4P-07.bmp",
    "4P-08.bmp",
    "4P-09.bmp",
    "4P-10.bmp",
    "4P-11.bmp",
    "4P-12.bmp",
    "4P-13.bmp",
    "4P-14.bmp",
    "4P-15.bmp",
    "4P-16.bmp"]

async def main(loop):
    n = 2
    delay = 100
    game_map = maps2p[0]
    
    print('Running docker commands....')
    os.system(f'powershell docker container stop $(docker container ls -q)')
    os.system(f'docker run -d --rm -p 8765:8765 blitzmmxxi/play --nbOfCrews={n} --gameConfig={game_map} --delayBetweenTicksMs={delay}')
    print('Done!')

    await asyncio.sleep(1)
    tasks = []
    for i in range(n):
        tasks.append(loop.create_task(application.run(f'Develop-{i}')))
        await asyncio.sleep(0.5)

    while not all(map(lambda x: x.done(), tasks)):
        await asyncio.sleep(1)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
    

