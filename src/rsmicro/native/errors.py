class RSmicroNativeError(RuntimeError):
    """Base error raised by the native runtime integration."""
    def __init__(self, message, *, operation=None, status=None, status_name=None, library_path=None):
        super().__init__(message); self.operation=operation; self.status=status; self.status_name=status_name; self.library_path=library_path

class NativeLibraryNotFoundError(RSmicroNativeError): pass
class NativeLibraryLoadError(RSmicroNativeError): pass
class NativeAbiMismatchError(RSmicroNativeError): pass
class NativeImageError(RSmicroNativeError): pass
class NativeMemoryError(RSmicroNativeError): pass
class NativeModeError(RSmicroNativeError): pass
class NativeTagError(RSmicroNativeError): pass
class NativeWriteError(RSmicroNativeError): pass
class NativeForceError(RSmicroNativeError): pass
class NativeFaultError(RSmicroNativeError): pass
class NativeHalError(RSmicroNativeError): pass
class NativeSimulationError(RSmicroNativeError): pass
