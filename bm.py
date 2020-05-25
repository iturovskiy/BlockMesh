import blockmesh.model as model
import argparse
import os


def bm_status(args):
    """Обработка ветви: bm.py status"""
    path = os.path.join(os.getcwd(), args.path)
    m = None
    try:
        print("Processing...")
        m = model.Model.load(path) if args.full else model.Model.load_simple(path)
    except NotADirectoryError:
        print(f"Error: There is no such directory: {path}")
    except FileNotFoundError:
        print(f"Error: There is no blockmesh model in {path}. You have to create new.")
    if m:
        print(f"Success! Blockmesh model exists.\n"
              f"{'Full' if args.full else 'Short'} info:\n"
              f"Mod:\t\t{m.mod.name}")
        if args.full:
            stat = m.get_stat()
            for k in stat:
                print(f"{k}:\t{stat[k]}")
        else:
            print(f"Timestamp:\t{m.model_time.time}\n"
                  f"Performed:\t{m.performed}\n"
                  f"Stg number:\t{m.stg_num}\n"
                  f"Usr number:\t{m.usr_num}")
        print(f"Duration 1:\t{m.duration[0]}\n"
              f"Duration 2:\t{m.duration[1]}\n")


def bm_init(args):
    """Обработка ветви: bm.py init"""
    path = os.path.join(os.getcwd(), args.path)
    try:
        print("Initing new blockmesh model...")
        m = model.Model(model.node.Mod[args.MOD], path, args.N_STG, args.N_USR, args.DUR_1, args.DUR_2)
        m.init()
        m.save()
        print(f"Success!")
    except Exception as e:
        print(f"Error: {e}")


def bm_run(args):
    """Обработка ветви: bm.py run"""
    path = os.path.join(os.getcwd(), args.path)
    try:
        print("Loading model...")
        m = model.Model.load(path)
        print(f"Running model for {args.ROUNDS}...")
        m.perform(args.ROUNDS)
        print(f"Saving...")
        m.save()
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")


def parse_args():
    """
    Парсер командной строки. \n
    Использование: \n
    bm.py [-h] {status,init,run} ... \n
    bm.py status [-h] [-p path] [-f] \n
    bm.py init [-h] [-p path] {Classic, Modified} N_STG N_USR DUR_1 DUR_2 \n
    bm.py run [-h] [-p path] ROUNDS \n
    :return: Распаршенные аргументы командной строки
    """
    parser = argparse.ArgumentParser(description="Command line for blockmesh model")
    sub_parser = parser.add_subparsers(help="Available sub-commands")

    # status branch
    parser_status = sub_parser.add_parser("status", help="Check and return status of blockmesh model")
    parser_status.add_argument("-p", dest="path", metavar="path", type=str, default="",
                               help="Path to directory containing blockmesh model")
    parser_status.add_argument("-f", dest="full", action='store_true', help="Load and check whole blockmesh model. "
                                                                            "Gives more info")
    parser_status.set_defaults(func=bm_status)

    # init branch
    parser_init = sub_parser.add_parser("init", help="Initialisation of new blockmesh model")
    parser_init.add_argument("-p", dest="path", metavar="path", type=str, default="",
                             help="Path to directory containing blockmesh model")
    parser_init.add_argument("MOD", choices=['Classic', 'Modified'], type=str, help="Mod of blockmesh model")
    parser_init.add_argument("N_STG", type=int, help="Number of storage-nodes. Must be > 0")
    parser_init.add_argument("N_USR", type=int, help="Number of user-nodes. Must be >= N_STG")
    parser_init.add_argument("DUR_1", type=int, help="Duration of 1st step")
    parser_init.add_argument("DUR_2", type=int, help="Duration of 2st step")
    parser_init.set_defaults(func=bm_init)

    # run branch
    parser_run = sub_parser.add_parser("run", help="Run blockmesh simulation")
    parser_run.add_argument("ROUNDS", type=int, help="Number of rounds to perform. Must be > 0")
    parser_run.add_argument("-p", dest="path", metavar="path", type=str, default="",
                            help="Path to directory containing blockmesh model")
    parser_run.set_defaults(func=bm_run)

    return parser.parse_args()


# status -p test/test_new_bm -f
# init -p test/test_new_bm Classic 10 100 60 10
# run -p test/test_new_bm 10
if __name__ == "__main__":
    parsed = parse_args()
    parsed.func(parsed)
