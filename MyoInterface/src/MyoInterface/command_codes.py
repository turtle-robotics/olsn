
class EmgMode:
    off = 0
    record_raw_emg = 2
    record_filtered_emg =3

class ImuMode:
    off =0
    send_data = 1
    send_event = 2
    send_all = 3
    send_raw = 4

class ClassifierMode:
    disabled = 0
    enabled = 1

class Commands:
    set_mode=1
    vibrate=3
    deep_sleep=4
    vibrate2 = 7
    set_sleep_mode = 9
    unlock = 10
    user_action = 11

class SleepModes:
    normal = 0
    never_sleep = 1

class UnlockModes:
    relock_immediately = 0
    relock_after_time_out = 1
    remain_unlocked_until_lock_command = 2

class SleepModes:
    normal = 0
    never_sleep = 1