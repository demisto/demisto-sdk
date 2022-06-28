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

##### Invalid images relative paths in pack readme
![Identity with High Risk Score](doc_files/High_Risk_User.png)
![Identity with High Risk Score](home/test1/test2/doc_files/High_Risk_User.png)
<img src="../../doc_files/Access_investigation_-_Generic_4_5.png"/>
![Account Enrichment](Insert the link to your image here)

##### images absolute paths
![Identity with High Risk Score](https://github.com/demisto/content/raw/test1.png)
![Identity with High Risk Score](https://raw.githubusercontent.com/demisto/content/raw/test1.png)
<img src="https://raw.githubusercontent.com/demisto/content/raw/test1.jpg" width="757" height="54">

#### paths that should not be caught
!command host="ip" action="test" src="https://github.com/demisto/content/raw/test3.png" state="present"
