from demisto_sdk.commands.validate_poc.validate_manager import ValidateManager

file_path = "/Users/yhayun/dev/demisto/content/Packs/CrowdStrikeFalcon"
validate_manager = ValidateManager(file_path)
flag = validate_manager.run()
print(flag)
