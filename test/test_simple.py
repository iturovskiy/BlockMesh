import os
from blockmesh.node import *
from shutil import rmtree


def test_simple(mod):
    t = ModelTime()
    pwd = os.path.join(os.getcwd(), f'test_simple_{mod.name}')
    try:
        rmtree(pwd)
    except FileNotFoundError:
        pass
    stg = [Storage(mod, os.path.join(pwd, 'Storages', f'stg_{i}'), t) for i in range(2)]
    stg[1].join_bm(stg[0])
    usr = [User(mod, os.path.join(pwd, 'Users', f"usr_{i}"), f"user{i}", f"sign{i}", stg[i % len(stg)]) for i in range(3)]
    t.tick()
    usr[0].perform([usr[1].addr], {"info": "1 block"})
    usr[1].perform([usr[2].addr], {"info": "2 block"})
    #
    t.tick()
    for s in stg:
        s.perform_step_1()
    for s in stg:
        s.perform_step_2()
    #
    t.tick()
    for s in stg:
        s.perform_step_1()
    for s in stg:
        s.perform_step_2()
    #
    for s in stg:
        s.save()
    for u in usr:
        u.save()


if __name__ == '__main__':
    test_simple(Mod.Classic)
    test_simple(Mod.Modified)
