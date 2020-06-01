#!/usr/bin/env python3

from prompt_toolkit import Application


def main(full_screen=True):
    app = Application(full_screen=full_screen)
    app.run()


if __name__ == "__main__":
    # main(full_screen=False)
    main()
