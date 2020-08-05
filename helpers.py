import csv
import json
import sys
import os
import logging
import binascii
import io
import time
import contextlib
import cProfile
import pstats

from functools import wraps
from contextlib import ContextDecorator
from logging.handlers import TimedRotatingFileHandler


def setup_logging(log_level=logging.INFO, log_path="logs/", log_file="app.log"):
    if not os.path.exists(log_path):
        os.mkdir(log_path)

    null_handler = logging.NullHandler()
    logging.basicConfig(level=log_level, handlers=[null_handler])

    logging_format = logging.Formatter(
        "%(asctime)s [%(levelname)s] -- [%(name)s:%(module)s/%(funcName)s] -- %(message)s",
        datefmt="%H:%M:%S"
    )

    # Set handler for logging to console.
    # console_handler = logging.StreamHandler()  # Log to stderr.
    console_handler = logging.StreamHandler(sys.__stdout__)  # Log to stdout.
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging_format)

    # Set up rotating file handler.
    file_handler = TimedRotatingFileHandler(log_path + log_file, when="d", interval=1, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging_format)

    logger = logging.getLogger()
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def write_to_csv(filename, fieldnames, data):
    with open(filename, mode='w') as csv_file:
        fieldnames = fieldnames
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def write_to_json(filename, data):
    with open(filename, mode='w') as json_file:
        json_data = json.dumps(data)
        json_file.write(json_data)


@contextlib.contextmanager
def profile():
    profile = cProfile.Profile()
    profile.enable()
    yield
    profile.disable()
    stream = io.StringIO()
    stats = pstats.Stats(profile, stream=stream).sort_stats("cumulative")
    stats.print_stats()
    # stats.print_callers()
    print(stream.getvalue())


def timeit(f):
    @wraps(f)
    def wrap(*args, **kw):
        start = time.time()
        result = f(*args, **kw)
        end = time.time()
        elapsed = end - start
        print(f"func: {f.__name__}, args: [{args}, {kw}], time: {elapsed}s")
        return result
    return wrap
