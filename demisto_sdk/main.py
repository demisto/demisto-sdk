import sys
from demisto_sdk.core import DemistoSDK


def main():
    # TODO: Typings and docstrings
    sdk = DemistoSDK()
    return sdk.parse_args()


if __name__ == '__main__':
    sys.exit(main())
