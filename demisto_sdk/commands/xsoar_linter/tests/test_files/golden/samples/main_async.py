"""Sample: main defined as an async function."""


async def main() -> None:
    params = demisto.params()
    print(params)


async def helper(value):
    return value
