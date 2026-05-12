from functools import cached_property
from pathlib import Path
from typing import List, Optional

from junitparser import Failure, JUnitXml, Skipped, TestCase

from demisto_sdk.commands.common.StrEnum import StrEnum


class TestStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    UNKNOWN = "UNKNOWN"


class TestType(StrEnum):
    UNIT_TESTS = "unit-tests"
    INTEGRATION_TESTS = "integration-tests"
    GRAPH_TESTS = "graph-tests"


class TestResult:
    def __init__(
        self,
        name: str,
        status: TestStatus,
        time: float,
        _type: TestType,
        message: Optional[str] = None,
    ):
        self.name = name
        self.status = status
        self.time = time
        self.message = message
        self.type = _type

    @property
    def is_unit_test(self) -> bool:
        return self.type == TestType.UNIT_TESTS

    @property
    def is_integration_test(self) -> bool:
        return self.type == TestType.INTEGRATION_TESTS

    @property
    def is_graph_test(self) -> bool:
        return self.type == TestType.GRAPH_TESTS

    @property
    def has_failed(self) -> bool:
        return self.status == TestStatus.FAILED

    @property
    def has_skipped(self) -> bool:
        return self.status == TestStatus.SKIPPED

    @property
    def has_passed(self) -> bool:
        return self.status == TestStatus.PASSED

    def __str__(self) -> str:
        return f"{self.name}(status={self.status}, time={self.time} seconds)"

    def __eq__(self, other):
        return (
            self.name == other.name
            and self.status == other.status
            and self.message == other.message
        )

    def __hash__(self):
        return hash((self.name, self.status, self.message))


class PytestTestSuite:
    def __init__(
        self,
        failures: int,
        skipped: int,
        num_of_tests: int,
        time: float,
        test_cases: List[TestCase],
        _type: TestType,
    ):
        self.failures = failures
        self.skipped = skipped
        self.num_of_tests = num_of_tests
        self.passed = self.num_of_tests - skipped - failures
        self.time = time
        self.test_cases = test_cases
        self.type = _type

    @cached_property
    def test_results(self) -> List[TestResult]:
        test_results = []
        for tc in self.test_cases:
            name = f"{tc.classname}.{tc.name}"
            time = tc.time
            message = None
            status = TestStatus.UNKNOWN
            if not tc.result:
                status = TestStatus.PASSED
            else:
                for result in tc.result:
                    if isinstance(result, Failure):
                        status = TestStatus.FAILED
                    if isinstance(result, Skipped):
                        status = TestStatus.SKIPPED
                    message = result.message

            test_results.append(
                TestResult(
                    name=name,
                    time=time,
                    status=status,
                    message=message,
                    _type=self.type,
                )
            )

        return test_results

    @property
    def failed_tests(self) -> List[TestResult]:
        if self.failures > 0:
            return [
                test_result
                for test_result in self.test_results
                if test_result.has_failed
            ]
        return []

    @property
    def skipped_tests(self) -> List[TestResult]:
        if self.skipped > 0:
            return [
                test_result
                for test_result in self.test_results
                if test_result.has_skipped
            ]
        return []

    @property
    def passed_tests(self) -> List[TestResult]:
        if self.passed > 0:
            return [
                test_result
                for test_result in self.test_results
                if test_result.has_passed
            ]
        return []

    @property
    def failed_unit_tests(self) -> List[TestResult]:
        return [
            test_result for test_result in self.failed_tests if test_result.is_unit_test
        ]

    @property
    def failed_integration_tests(self) -> List[TestResult]:
        return [
            test_result
            for test_result in self.failed_tests
            if test_result.is_integration_test
        ]

    @property
    def failed_graph_tests(self) -> List[TestResult]:
        return [
            test_result
            for test_result in self.failed_tests
            if test_result.is_graph_test
        ]


class JunitParser:
    def __init__(self, junit_file_path: Path):
        self.junit_file_path = junit_file_path

    @property
    def test_type(self):
        """
        Get the test-type based on junit file path.
        """
        junit_abs_path = str(self.junit_file_path.absolute())
        if TestType.UNIT_TESTS in junit_abs_path:
            _type = TestType.UNIT_TESTS
        elif TestType.INTEGRATION_TESTS in junit_abs_path:
            _type = TestType.INTEGRATION_TESTS
        else:
            _type = TestType.GRAPH_TESTS

        return _type

    @property
    def test_suites(self) -> List[PytestTestSuite]:
        test_suites = JUnitXml.fromfile(str(self.junit_file_path))
        return [
            PytestTestSuite(
                failures=int(test_suite.failures),
                skipped=int(test_suite.skipped),
                num_of_tests=int(test_suite.tests),
                time=test_suite.time,
                test_cases=list(test_suite),
                _type=self.test_type,
            )
            for test_suite in test_suites
        ]
