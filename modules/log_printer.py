def print_log(name, message, end = "\n"):
    print("[LOG] {:<13}: {}".format(name, message), end = end)

def print_err(message):
    print("\t[ERROR] {}".format(message))