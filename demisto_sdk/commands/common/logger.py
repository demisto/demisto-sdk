DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

FILE_LOG_RECORD_FORMAT = "[%(asctime)s] - [%(threadName)s] - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s"

CONSOLE_LOG_RECORD_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
CONSOLE_LOG_RECORD_FORMAT_SHORT = "[%(asctime)s] [%(levelname)s] "

DEMISTO_LOG_ALLOWED_ESCAPES = [  # The order of the list is by priority.
    ("green", 32),
    ("red", 91),
    ("yellow", 93),
    ("cyan", 36),
    ("blue", 34),
    ("orange", 33),
    ("purple", 35),
    ("bold", 1),
    ("underline", 4),
    ("lightblue", 94),
]
