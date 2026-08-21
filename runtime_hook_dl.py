
import sys, os, importlib.util
_here = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
# The _downloader.py is bundled as a data file; load it explicitly
for candidate_dir in [os.path.join(_here, "_internal"), _here]:
    p = os.path.join(candidate_dir, "_downloader_runtime.py")
    if os.path.exists(p):
        spec = importlib.util.spec_from_file_location("_downloader", p)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_downloader"] = mod
        spec.loader.exec_module(mod)
        break
