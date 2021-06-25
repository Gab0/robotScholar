import argparse
from . import Viewer, Parser


def parse_arguments():
    main_parser = argparse.ArgumentParser()

    subparser = main_parser.add_subparsers(
        title="parse",
        dest="command"
    )

    #viewer_parser = main_parser.add_subparsers(
    #        title="view",
    #        dest="viewer_command"
    #)

    Viewer.parse_arguments(subparser.add_parser("view"))
    Parser.parse_arguments(subparser.add_parser("parse"))

    return main_parser.parse_args()


def main():
    k = parse_arguments()
    print(k)
    if k.command == 'parse':
        Parser.execute(k)
    elif k.command == 'view':
        Viewer.execute(k)
    else:
        print("No command selected!")
        sys.exit(1)


if __name__ == "__main__":
    main()
