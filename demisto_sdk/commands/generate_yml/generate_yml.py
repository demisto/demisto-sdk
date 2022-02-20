"""This file is a part of the generating yml design. Generating a yml file from a python file."""
import importlib.util
import types


class YMLGenerator:
    """The YMLGenerator class preforms the following:
        1. Obtain the relevant YMLMetadataCollector object from the specified python file.
        2. Make a list of the decorated functions from the specified python file.
        3. Use metadata_collector to collect the details from the relevant python file.
        4. Generate YML file based on the details collected.
    """

    def __init__(self, filename):
        self.functions = []
        self.filename = filename
        self.details_collector = None
        self.file_import = None
        self.import_the_details_collector()
        print(f"{self.details_collector}")

    def import_the_details_collector(self):
        """Find the details object in the python file and import it."""
        spec = importlib.util.spec_from_file_location("metadata_collector", self.filename)
        # The self.file_import object will be used later to identify wrapped functions.
        self.file_import = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.file_import)
        # Here we assume the details_collector object will be called 'details'.
        self.details_collector = self.file_import.metadata_collector

    def generate(self):
        """The main method. Collect details and write the yml file."""
        # Collect the wrapped functions wit details.
        self.collect_functions()
        # Make sure when they are run, only collecting data will be preformed.
        self.details_collector.set_collect_data(True)
        # Run the functions and by that, collect the data.
        self.run_functions()
        # Write the yml file according to the collected details.
        self.write_yaml()
        # Make sure the functions are back to normal running state.
        self.details_collector.set_collect_data(False)

    def collect_functions(self):
        """Collect the wrapped functions from the python file."""
        for item in dir(self.file_import):
            new_function = getattr(self.file_import, item)
            # if it is a YMLMetadataCollector wrapper, add it to the list.
            if callable(new_function) and isinstance(new_function, types.FunctionType) and 'YMLMetadataCollector' in repr(new_function):
                print(f"item {item}")
                self.functions.append(new_function)

        print(f"functions found: {self.functions}")

    def run_functions(self):
        """Run the functions found."""
        print("running functions")
        for function in self.functions:
            print(f"function run: {function}")
            function()

    def write_yaml(self):
        """Write the yml file based on the collected details."""
        print("writing...")
        print(f"{self.details_collector.conf}")
        print(f"{self.details_collector.docs}")
        print(f"{self.details_collector.commands}")


# Example Usage of generating yml file. Will be positioned where unify is called.
yml_generator = YMLGenerator(filename='./example_integration.py')
yml_generator.generate()
