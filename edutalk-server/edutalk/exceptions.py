class BaseError(Exception):
    """Base error class"""
    pass


class UtilError(BaseError):
    """Base util error class"""
    pass


class CCMAPIError(UtilError):
    """Raised when a ccm_api returned status is not `ok`"""
    pass
