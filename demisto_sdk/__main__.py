import os
from demisto_sdk.main import main


def console_entry() -> None:
    os._exit(main())


if __name__ == '__main__':
    main()
