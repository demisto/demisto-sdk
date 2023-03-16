PhishTank is a free community site where anyone can submit, verify, track and share phishing data.
This integration was integrated and tested with version 1.0.1 of PhishTank.
## Configure PhishTankV2 on Cortex XSOAR

### Relative urls test-
[Good link](https://www.good.co.il)
[Good link2](https://example.com)
test link- [invalid relative 1](relative1.com)
[invalid relative 2](www.relative2.com) another test
[empty link]()
<a href="https://hreftesting.com"> good href test </a>
<a href="hreftesting.com"> href tests </a>
<a href="www.hreftesting.com"> www href tests </a>


##### images relative paths valid
[![Identity with High Risk Score](binary_files/0.jpg)](https://github.com/demisto/content/raw/test2.png)
![Identity with High Risk Score](binary_files/0.jpg)
    ![Identity with High Risk Score](binary_files/0.jpg)
<img src="binary_files/0.jpg"/>

#### paths that should not be caught
!command host="ip" action="test" src="https://github.com/demisto/content/raw/test3.png" state="present"
