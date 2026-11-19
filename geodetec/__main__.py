"""Punto de entrada: ``python -m geodetec [--consola]``."""
import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--consola" in argv:
        from .consola import modo_consola
        modo_consola()
    else:
        from .gui import modo_gui
        modo_gui()


if __name__ == "__main__":
    main()
