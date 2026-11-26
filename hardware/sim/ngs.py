# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Thomas Legrand
"""Minimal driver for the ngspice shared library shipped with KiCad 10 (ctypes, nothing to install).

    from ngs import run
    vecs = run(netlist_text, "op")            # {"v(out)": [..], ...}
"""
import ctypes
import os

DLL = os.environ.get("NGSPICE_DLL", r"C:\Program Files\KiCad\10.0\bin\ngspice.dll")


class _VecInfo(ctypes.Structure):
    _fields_ = [("name", ctypes.c_char_p), ("type", ctypes.c_int), ("flags", ctypes.c_short),
                ("realdata", ctypes.POINTER(ctypes.c_double)), ("compdata", ctypes.c_void_p),
                ("length", ctypes.c_int)]


_SEND_CHAR = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
_SEND_STAT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
_EXIT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
_LOG = []


@_SEND_CHAR
def _on_char(text, ident, user):
    _LOG.append(text.decode(errors="replace"))
    return 0


@_SEND_STAT
def _on_stat(text, ident, user):
    return 0


@_EXIT
def _on_exit(status, unload, quit_, ident, user):
    return 0


_lib = None


def _load():
    global _lib
    if _lib is None:
        os.add_dll_directory(os.path.dirname(DLL))
        _lib = ctypes.CDLL(DLL)
        _lib.ngSpice_Init(_on_char, _on_stat, _on_exit, None, None, None, None)
        _lib.ngGet_Vec_Info.restype = ctypes.POINTER(_VecInfo)
        _lib.ngSpice_CurPlot.restype = ctypes.c_char_p
        _lib.ngSpice_AllVecs.restype = ctypes.POINTER(ctypes.c_char_p)
    return _lib


def run(netlist, analysis):
    """Loads `netlist` (text, without .end), runs `analysis` ("op", "dc ...", "tran ..."),
    returns every vector of the resulting plot as {name: list of floats}."""
    lib = _load()
    _LOG.clear()
    lines = [ln for ln in netlist.strip().splitlines()] + [".end"]
    arr = (ctypes.c_char_p * (len(lines) + 1))(*[ln.encode() for ln in lines], None)
    lib.ngSpice_Command(b"remcirc")
    if lib.ngSpice_Circ(arr):
        raise RuntimeError("netlist rejected:\n" + "".join(_LOG))
    if lib.ngSpice_Command(analysis.encode()) or any("aborted" in s or "Fatal" in s for s in _LOG):
        raise RuntimeError("analysis failed:\n" + "".join(_LOG))
    plot = lib.ngSpice_CurPlot()
    names = lib.ngSpice_AllVecs(plot)
    out, i = {}, 0
    while names[i]:
        name = names[i].decode()
        info = lib.ngGet_Vec_Info(f"{plot.decode()}.{name}".encode()).contents
        if info.realdata:
            out[name.lower()] = [info.realdata[k] for k in range(info.length)]
        i += 1
    return out
