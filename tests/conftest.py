import os
import sys
from pathlib import Path
import warnings

# Adiciona o diretório src ao PYTHONPATH
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)

# Filtra os warnings específicos do SWIG
warnings.filterwarnings("ignore", category=DeprecationWarning, 
                      message="builtin type SwigPyPacked has no __module__ attribute")
warnings.filterwarnings("ignore", category=DeprecationWarning, 
                      message="builtin type SwigPyObject has no __module__ attribute")
warnings.filterwarnings("ignore", category=DeprecationWarning, 
                      message="builtin type swigvarlink has no __module__ attribute") 