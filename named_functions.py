from builtins   import print as builtin_print
from functools  import wraps as functools_wraps
from typing     import Any

class Style:
    def __init__(self) -> None:
        pass

class Name(object):
    global print
    
    def __init__(self, name) -> None:
        self.name = name

    def __call__(self, fn) -> Any:
        global print

        def temp_print(*args, **kwargs):
            builtin_print(self.name, *args, **kwargs)

        @functools_wraps(fn)
        def wrapper_name(*args, **kwargs):
            global print

            # prev_print  = print         # 1) Save current print function.
            print       = temp_print    # 2) Replace it with our print function.
            fn(*args, **kwargs)         # 3) Call wrapped function.
            print       = builtin_print    # 4) Restore saved print function.

        return wrapper_name

# def name(name: str, func):
#     global print
#
#     def temp_print(*args, **kwargs):
#         builtin_print(name, *args, **kwargs)
#
#     def wrapper_name(*args, **kwargs):
#         prev_print  = print         # 1) Save current print function.
#         print       = temp_print    # 2) Replace it with our print function.
#         func(*args, **kwargs)       # 3) Call wrapped function.
#         print       = prev_print    # 4) Restore saved print function.
#
#     return wrapper_name

# # Override builtin print function which prefixes
# # calls with stylized names.
# def print(*args, **kwargs):
#     global g_thread_print_names
#
#     id = current_thread().ident
#     prefix = g_thread_print_names.get(id)
#     if prefix is not None:
#         args = (prefix, *args)
#     builtin_print(*args, **kwargs)
#     return