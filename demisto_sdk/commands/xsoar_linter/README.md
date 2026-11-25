## xsoar-lint

### Overview
Run the xsoar lint on the given paths.

### Options
The python files to run on.

**Examples**
1. `demisto-sdk xsoar-lint Packs/Some_Pack/Integrations/Some_Integration/Some_Integration.py`

2. `demisto-sdk xsoar-lint Packs/Some_Pack/Integrations/Some_Integration/Some_Integration.py Packs/Some_Pack2/Integrations/Some_Integration2/Some_Integration2.py`

### Disable comments
To turn off a rule, add a comment with the `xsoar-lint` prefix. A rule can be named by its code (`E9002`) or its name (`print-exists`).

```python
print("debug")  # xsoar-lint: disable=print-exists

# xsoar-lint: disable-next=E9002
print("debug")
```

- `disable=<rules>`: at the end of a code line, applies to that line, or to the whole block if the line opens one (for example `def`). On its own line, applies until the end of the block it is in, or until `enable=<rules>`.
- `disable-next=<rules>`: applies to the next line only.
- `skip-file`: ignores the whole file. The file must still parse.
- `skip-parse-file`: skips the file before it is parsed, and logs it. Use it only for files that use Python syntax newer than the Python demisto-sdk runs on, which would otherwise fail with `E0001`. It must be on its own line, and it works only with the `xsoar-lint` prefix.

The `# pylint:` prefix still works the same way, so existing comments don't need to change.
