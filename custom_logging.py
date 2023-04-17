import logging
import sys


def set_up_logging():
    # set up logging to stdout and file
    # set a more pleasant stdout logging format
    formatter_defaults = {"prefix": "", "postfix": ""}
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(
        logging.Formatter(
            "%(prefix)s%(message)s%(postfix)s", defaults=formatter_defaults
        )
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler("progress.log", encoding="utf-8"),
            stdout_handler,
        ],
    )
