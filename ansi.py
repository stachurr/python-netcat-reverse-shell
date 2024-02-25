def red(text: str, reset: bool = True):
    retstr = '\x1b[91m' + text
    if reset:
        retstr += '\x1b[0m'
    return retstr