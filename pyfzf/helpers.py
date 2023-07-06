import io
import time
import contextlib
import cProfile
import pstats

from functools import wraps
from contextlib import ContextDecorator


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
