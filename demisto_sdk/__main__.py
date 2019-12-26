import sys
from demisto_sdk.main import main


def console_entry() -> None:
    sys.exit(main())


if __name__ == '__main__':
    main()
