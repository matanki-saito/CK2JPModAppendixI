import os
import sys


def main():
    for k, v in os.environ.items():
        print("{key} : {value}".format(key=k, value=v))
    print(sys.argv)


if __name__ == "__main__":
    main()
