class AppException(Exception):

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400
    ):

        self.message = message

        self.error_code = error_code

        self.status_code = status_code


# =========================================
# VERIFICATION PIPELINE EXCEPTIONS
# =========================================

class FieldExtractionError(Exception):
    pass


class VerificationError(Exception):
    pass


class FraudDetectionError(Exception):
    pass


class DecisionError(Exception):
    pass