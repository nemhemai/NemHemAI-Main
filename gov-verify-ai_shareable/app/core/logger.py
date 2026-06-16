import logging
import sys

import structlog


def setup_logging():

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(
                fmt="iso"
            ),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
        ]
    )


logger = structlog.get_logger()


def get_logger(name=None):

    return logger