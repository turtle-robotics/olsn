from MyoInterface.MyoInterface import MyoInterface
import os
import asyncio

interface = MyoInterface()
path = r'C:\Users\madwill\Desktop\Dr. Graves Show Case\Recording\pinkey'
async def function(interface:MyoInterface):
    # await interface.connect()
    await interface.record_raw_emg(os.path.join(path,f'pinkey_hold.csv'))
interface.run_and_display_eeg(function,connected=True)
# interface.connect_and_run_function(function)
# asyncio.run(function(interface))