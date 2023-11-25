from MyoInterface.MyoInterface import MyoInterface
import asyncio
import os
path = r'C:\Users\madwill\Desktop\Dr. Graves Show Case\Recording\tapping\bent arm side'
interface = MyoInterface()
async def function(interface:MyoInterface):
    await interface.connect()
    await interface.stream_raw_emg()
# interface.connect_and_run_function(function)


asyncio.run(function(interface))
