import subprocess


def initialize_matrix(rows, cols):
    return [[0 for col in range(cols)] for row in range(rows)]


def print_matrix(matrix):
    """Pretty print the scoring matrix.

    ex:
    0   0   0   0   0   0
    0   2   1   2   1   2
    0   1   1   1   1   1
    0   0   3   2   3   2
    0   2   2   5   4   5
    0   1   4   4   7   6
    """

    s = [[("  " + str(e)) for e in row] for row in matrix]
    lens = [max(map(len, col)) for col in zip(*s)]
    fmt = "".join("{{:{}}}".format(x) for x in lens)
    table = [fmt.format(*row) for row in s]
    print("\n".join(table))


# TODO: add support for specifying alternate find commands
def get_files_and_dirs(include_dirs=False, include_hidden=False):
    # recursively get all files, ignoring hidden files (-not -path '*/\.*)
    if include_dirs:
        if include_hidden:
            process = subprocess.Popen(["find", "."], stdout=subprocess.PIPE)
        else:
            process = subprocess.Popen(["find", ".",  "-not", "-path", "*/\.*"], stdout=subprocess.PIPE)
    else:
        if include_hidden:
            process = subprocess.Popen(["find", ".", "-type", "f"], stdout=subprocess.PIPE)
        else:
            process = subprocess.Popen(["find", ".",  "-not", "-path", "*/\.*", "-type", "f"], stdout=subprocess.PIPE)

    out, err = process.communicate()
    out = out.decode("UTF-8").split("\n")

    # remove empty str item from list
    # remove current dir indicator if output with find (".")
    if out[0] == ".":
        out = out[1:-1]
    else:
        out = out[0:-1]

    lines = []
    for line in out:
        line = line.replace("./", "", 1)
        lines.append(line)

    return lines


if __name__ == "__main__":
    import time
    start_time = time.time()
    rv = get_files_and_dirs()
    duration = time.time() - start_time
    print(duration)
