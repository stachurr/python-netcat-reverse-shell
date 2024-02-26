class color:
    def __init__(self, r: int, g: int, b: int) -> None:
        self.r: int = r
        self.g: int = g
        self.b: int = b

def red(text: str, reset: bool = True):
    retstr = '\x1b[91m' + text
    if reset:
        retstr += '\x1b[0m'
    return retstr