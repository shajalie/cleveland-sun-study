"""Use Blender's bundled Intel OIDN HDR filter on linear HDR lightmaps."""

import ctypes as C, os, numpy as np
from pathlib import Path


class LightmapDenoiser:
    def __init__(self, blender):
        folder = Path(blender).parent / "blender.shared"
        self.directory = os.add_dll_directory(str(folder))
        self.lib = C.CDLL(str(folder / "OpenImageDenoise.dll"))

        def bind(name, ret, args):
            f = getattr(self.lib, name)
            f.restype = ret
            f.argtypes = args
            return f

        self.new = bind("oidnNewDevice", C.c_void_p, [C.c_int])
        self.commit = bind("oidnCommitDevice", None, [C.c_void_p])
        self.filter = bind("oidnNewFilter", C.c_void_p, [C.c_void_p, C.c_char_p])
        self.image = bind(
            "oidnSetSharedFilterImage",
            None,
            [
                C.c_void_p,
                C.c_char_p,
                C.c_void_p,
                C.c_int,
                C.c_size_t,
                C.c_size_t,
                C.c_size_t,
                C.c_size_t,
                C.c_size_t,
            ],
        )
        self.commitfilter = bind("oidnCommitFilter", None, [C.c_void_p])
        self.execute = bind("oidnExecuteFilter", None, [C.c_void_p])
        self.error = bind(
            "oidnGetDeviceError", C.c_int, [C.c_void_p, C.POINTER(C.c_char_p)]
        )
        self.release = bind("oidnReleaseFilter", None, [C.c_void_p])
        self.device = self.new(1)
        self.commit(self.device)

    def apply(self, rgb):
        src = np.ascontiguousarray(rgb, dtype=np.float32)
        out = np.empty_like(src)
        h, w = src.shape[:2]
        f = self.filter(self.device, b"RT")
        flag = self.lib.oidnSetFilterBool
        flag.argtypes = [C.c_void_p, C.c_char_p, C.c_bool]
        flag.restype = None
        flag(f, b"hdr", True)
        for name, arr in [(b"color", src), (b"output", out)]:
            self.image(f, name, arr.ctypes.data, 3, w, h, 0, 0, 0)
        self.commitfilter(f)
        self.execute(f)
        msg = C.c_char_p()
        code = self.error(self.device, C.byref(msg))
        self.release(f)
        if code:
            raise RuntimeError(msg.value.decode())
        return np.maximum(out, 0)
