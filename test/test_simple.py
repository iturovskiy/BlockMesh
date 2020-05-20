import os
from blockmesh.node import *
from shutil import rmtree
from blockmesh.model import ModelTime


def prepare(mod, d, stg_num, usr_num):
    t = ModelTime()
    pwd = os.path.join(os.getcwd(), f'{d}{mod.name}')
    try:
        rmtree(pwd)
    except FileNotFoundError:
        pass
    stg = [Storage(mod, os.path.join(pwd, 'Storages', f'stg_{i}'), t) for i in range(stg_num)]
    for i in range(len(stg) - 1):
        stg[i + 1].join_bm(stg[i])
    usr = [User(mod, os.path.join(pwd, 'Users',
                                  f"usr_{i}"), f"user{i}", f"sign{i}", stg[i % len(stg)]) for i in range(usr_num)]
    return stg, usr, t


def stg_step(stg, t, dur=1):
    for i in range(dur):
        t.tick()
        for s in stg:
            s.perform_step_1()
        for s in stg:
            s.perform_step_2()


def usr_step(usr, sender: int, receivers: list):
    if sender >= len(usr) or sender < 0:
        raise ValueError()
    for recv in receivers:
        if recv >= len(usr) or recv < 0:
            raise ValueError()
    usr[sender].perform([usr[i].addr for i in receivers], {"info": f"{sender} -> {receivers}"})


def save(stgs=None, usrs=None):
    if stgs:
        for s in stgs:
            s.save()
    if usrs:
        for u in usrs:
            u.save()


def test_simple(mod):
    s_num = 2
    u_num = 3
    stg, usr, time = prepare(mod, "test_simple_", s_num, u_num)
    time.tick()
    usr_step(usr, 0, [1])
    usr_step(usr, 1, [2])
    stg_step(stg, time, 2)
    save(stg, usr)


def test_unavail(mod):
    s_num = 3
    u_num = 10
    stg, usr, time = prepare(mod, "test_unavail_", s_num, u_num)
    usr_step(usr, 0, [1, 2])
    time.tick()
    usr_step(usr, 4, [5])
    time.tick()
    usr_step(usr, 8, [6])
    time.tick()
    stg_step(stg, time, 3)


if __name__ == '__main__':
    # test_simple(Mod.Classic)
    # test_simple(Mod.Modified)
    test_unavail(Mod.Classic)
    test_unavail(Mod.Modified)
