import os
import sys


def main():
    for k, v in os.environ.items():
        try:
            print("{key} : {value}".format(key=k, value=v))
        except UnicodeEncodeError:
            pass
    print(sys.argv)


if __name__ == "__main__":
    main()
