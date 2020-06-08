import blockmesh.model as model
import argparse
import os


def bm_status(args):
    """Обработка ветви: bm.py status"""
    path = os.path.join(os.getcwd(), args.dir)
    m = None
    try:
        print("Processing...")
        m = model.Model.load(path)
    except NotADirectoryError:
        print(f"Error: There is no such directory: {path}")
    except FileNotFoundError:
        print(f"Error: There is no blockmesh model in {path}. You have to create new.")
    if m:
        print(f"Info:\n"
              f"Mod:\t\t{m.mod.name}\n"
              f"Stg number:\t{m.stg_num}\n"
              f"Usr number:\t{m.usr_num}")
        stat = m.get_stat()
        for k in stat:
            print(f"{k}:\t{stat[k]}")
        print(f"Duration 1:\t{m.duration[0]}\n"
              f"Duration 2:\t{m.duration[1]}\n"
              f"Sync blocks:\t{m.get_sync_count()}")
        if args.plot:
            m.draw_plot()
        if args.graph:
            m.draw_graph()


def bm_init(args):
    """Обработка ветви: bm.py init"""
    path = os.path.join(os.getcwd(), args.dir)
    try:
        print("Initialisation of new blockmesh model...")
        m = model.Model(model.node.Mod[args.MOD], path, args.N_STG, args.N_USR, args.DUR_1, args.DUR_2)
        m.init()
        m.save()
        print(f"Success!")
    except Exception as e:
        print(f"Error: {e}")


def bm_run(args):
    """Обработка ветви: bm.py run"""
    path = os.path.join(os.getcwd(), args.dir)
    try:
        print("Loading model...")
        m = model.Model.load(path)
        print("Running model...")
        m.run()
        print(f"Saving...")
        m.save()
        if args.plot:
            m.draw_plot()
        if args.graph:
            m.draw_graph()
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")


def parse_args():
    """
    Парсер командной строки. \n
    Использование: \n
    bm.py [-h] {status,init,run} ... \n
    bm.py status [-h] [-d dir] [-P] [-G] \n
    bm.py init [-h] [-d dir] {Classic, Modified} N_STG N_USR DUR_1 DUR_2 \n
    bm.py run [-h] [-d dir] [-P] [-G] \n
    :return: Распаршенные аргументы командной строки
    """
    parser = argparse.ArgumentParser(description="Command line handle for blockmesh model")
    sub_parser = parser.add_subparsers(help="Available sub-commands")

    # status branch
    parser_status = sub_parser.add_parser("status", help="Check and return status of blockmesh model")
    parser_status.add_argument("-d", "--dir", dest="dir", metavar="dir", type=str, default="",
                               help="Path to directory containing blockmesh model")
    parser_status.add_argument("-P", "--plot", dest="plot", action='store_true', help="Draw plot")
    parser_status.add_argument("-G", "--graph", dest="graph", action='store_true', help="Draw graph")
    parser_status.set_defaults(func=bm_status)

    # init branch
    parser_init = sub_parser.add_parser("init", help="Initialisation of new blockmesh model")
    parser_init.add_argument("-d", "--dir", dest="dir", metavar="dir", type=str, default="",
                             help="Path to directory containing blockmesh model")
    parser_init.add_argument("MOD", choices=['Classic', 'Modified'], type=str, help="Mod of blockmesh model")
    parser_init.add_argument("N_STG", type=int, help="Number of storage-nodes. Must be > 0")
    parser_init.add_argument("N_USR", type=int, help="Number of user-nodes. Must be >= N_STG")
    parser_init.add_argument("DUR_1", type=int, help="Duration of 1st step")
    parser_init.add_argument("DUR_2", type=int, help="Duration of 2st step")
    parser_init.set_defaults(func=bm_init)

    # run branch
    parser_run = sub_parser.add_parser("run", help="Run blockmesh simulation")
    parser_run.add_argument("-d", "--dir", dest="dir", metavar="dir", type=str, default="",
                            help="Path to directory containing blockmesh model")
    parser_run.add_argument("-P", "--plot", dest="plot", action='store_true', help="Draw plot")
    parser_run.add_argument("-G", "--graph", dest="graph", action='store_true', help="Draw graph")
    parser_run.set_defaults(func=bm_run)

    return parser.parse_args()


if __name__ == "__main__":
    """
    status -d test/test_classic
    init -d test/test_classic Classic 10 100 300 60
    run -d test/test_classic -P -G -- works fine

    status -d test/test_mod
    init -d test/test_mod Modified 10 100 300 60
    run -d test/test_mod -P -G
    """
    parsed = parse_args()
    parsed.func(parsed)
