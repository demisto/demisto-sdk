
## coverage-analyze

### Overview
Generating and printing the coverage reports.

### Options
* **-i --input**
The .coverage file to analyze.
* **--default-min-coverage**
Default minimum coverage (for new files). The default value is 70.
* **--allowed-coverage-degradation-percentage**
Allowed coverage degradation percentage (for modified files). The default value is 1.0.
* **--no-cache**
Force download of the previous coverage report file.
* **--report-dir**
Directory of the coverage report files. The default value is ./coverage_report
* **--report-type**
The type of coverage report (posible values: 'text', 'html', 'xml', 'json' or 'all').
* **---no-min-coverage-enforcement**
Do not enforce minimum coverage.
* **--previous-coverage-report-url**
URL of the previous coverage report. The default value is https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/coverage-min.json

**Examples**:
1. print report of .coverge file - `demisto-sdk coverage-analyze -i .coverage`
2. create report of .coverge file - `demisto-sdk coverage-analyze -i .coverage --report-type html`
