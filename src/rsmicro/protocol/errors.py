from enum import IntEnum
class ErrorCode(IntEnum):
 BAD_FRAME=1; BAD_CRC=2; UNSUPPORTED_VERSION=3; UNSUPPORTED_MESSAGE=4; MALFORMED_PAYLOAD=5; INCOMPATIBLE_CAPABILITY=6; INVALID_MODE=7; STALE_PROGRAM_GENERATION=8; TAG_NOT_FOUND=9; TYPE_MISMATCH=10; NOT_WRITABLE=11; NOT_FORCEABLE=12; QUEUE_FULL=13; TRANSFER_IN_PROGRESS=14; TRANSFER_NOT_FOUND=15; TRANSFER_INCOMPLETE=16; TRANSFER_HASH_MISMATCH=17; IMAGE_INVALID=18; ACTIVATION_FAILED=19; SUBSCRIPTION_LIMIT=20; NODE_FAULTED=21; INTERNAL_ERROR=255
class RsmLinkError(Exception): pass
class RsmLinkConnectionError(RsmLinkError): pass
class RsmLinkTimeoutError(RsmLinkError): pass
class RsmLinkProtocolError(RsmLinkError): pass
class RsmLinkCompatibilityError(RsmLinkError): pass
class RsmLinkRemoteError(RsmLinkError):
 def __init__(self,message,*,request_id=0,code=ErrorCode.INTERNAL_ERROR,recoverable=False,details=None): super().__init__(message); self.request_id=request_id; self.code=code; self.recoverable=recoverable; self.details=details or {}
class RsmLinkTransferError(RsmLinkRemoteError): pass
class RsmLinkActivationError(RsmLinkRemoteError): pass
class RsmLinkTagError(RsmLinkRemoteError): pass
class RsmLinkSubscriptionError(RsmLinkRemoteError): pass
class RsmLinkNodeFaultError(RsmLinkRemoteError): pass
