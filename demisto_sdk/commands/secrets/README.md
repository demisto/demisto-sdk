# Secrets

**Run Secrets validator to catch sensitive data before exposing your code to public repository. Attach full path to whitelist to allow manual whitelists.**

**Arguments:**

* **--post-commit**
                       Whether the secretes validation is done after you committed your files.
                       This will help the command to determine which files it should check in its
                       run. Before you commit the files it should not be used. Mostly for build
                       validations. (default: False)

* **-wl WHITELIST, --whitelist WHITELIST**
                        Full path to whitelist file, file name should be "secrets_white_list.json".
                        (default: ./Tests/secrets_white_list.json)

### Examples
```
demisto-sdk secrets
```
This will run the secrets validator on your uncommited files.
<br/><br/>
```
demisto-sdk secrets -i ./Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml
```
This will run the secrets validator on the file located in ./Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml.
<br/><br/>
```
demisto-sdk secrets --post-commit
```
This will run the secrets validator on your files after you committed them.
<br/><br/>
```
demisto-sdk secrets -wl ./secrets_white_list.json
```
This will run the secrets validator on your files with your own whitelist file located in ./secrets_white_list.json.


## More About Secrets and Sensitive Data

Demisto's [content](https://github.com/demisto/content) repository is public and open source. It is important we don't commit secrets and sensitive data into this repositiry. Data we consider sensitive:

* Customer identifying data: anything that can identify an organization as our customer
* Customer environment information
* Passwords
* IPs
* Urls/domains
* Email addresses not for testing
* PII: personal identifying information
* Screenshots of third party products
* Screenshots that may contain any of the above data

**Important**: Be careful on what you post on PR comments and code review.
## Overview
This article's purpose is to teach you about how we detect secrets in demisto and how to whitelist them properly.

Secret detection will be done in the pre-commit stage, and also on the build stage. (
Notice if actual secrets were detected on the build stage, it means they were already exposed on a public repo,
 and you should alert the relevant people)


## White Listing

- Temporary white listing happens automatically for .yml files with context paths configured.
- The main whitelist file is secrets_white_list.json, this file is divided into 3 major parts:
IOCs, Generic Strings, and Integration specific strings.
- IOCs is divided further into types such as IPV4, IPV6, EMAILS, URLS and more.
- Secrets found via regex will only be tested against IOCs whitelist, so make extra sure if you whitelist an indicator to put it under the IOCs dict.
- Generic Strings are common words that you can find in integrations and scripts.
- If your integration requires a specific key word you can add it to the dict with a key that is similar to the relevant integration.
Example: A lot of false positives with CookieMonster were found, and you realize with your common sense that the term CookieMonster is not relevant to the generic words,
this is the proper time to create a new key in the file named "sesame street" and the value will be a list with "cookiemonster".
ONLY do this in the rare case the string does not fit logically anywhere else.
- Once you update the white list file with a string, it will be white listed globally for all integrations, even if it's integration specific.
- Only words of 5+ chars will be taken into account in the whitelist.
- Secrets found in content packs will be checked against both, the whitelist file provided in the WHITELIST argument, and in and the pack secrets file (.secrets-ignore).

- **Notice:** all words in whitelist must be lowercase. In order to lower case strings use **command+shift+u**

## Ignoring single lines / multi lines

Why would we want to ignore a line instead of whitelisting it?
- The line has dynamic secret/false positive (like a hash)
- very long strings that are pretty random (like a regex)
- Anything that does not make enough sense to be on a shared whitelist

Notice the phrases do not have to be in a comment, and not on their own, so you could mix them with any line.

**Single Line Secerts Disable**

Python
```
i_wrote_too_much_words_without_any_seperator =  ReadableContentsFormat.SomeExample # disable-secrets-detection
```

**Multi Line Secerts Disable**

Python
```
# About the drop some mean regex right now disable-secrets-detection-start
TONS_OF_REGEX = r'(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1' \
             r'[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::'\
             r'(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]'\
             r'{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|'\
             r'(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|'\
             r'(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}'\
             r'|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){3}?)'
# Drops the mic disable-secrets-detection-end
```

## How secrets detection / whitelisting works

**Secrets Detection**

- Any string with high entropy, the more random and longer it is the higher entropy it will have.
The average string have entropy of between 2 to 3.4 entropy,
but notice some longer strings of variable names could have entropy of 3.6 and a bit more.
- As complimentary mechanism we are using is regex in order to detect mostly IOCs with high risk of low entropy,
an example would be IPV4 which can have a lot of repeating characters, reducing it's randomness.
- Secrets detection is being done on the file level, on the line level, and then on the string level.
- Files that are being currently scanned are: added/modified files of formats: '.yml', '.py', '.json', '.md', '.txt', '.sh', '.ini', '.eml', '', '.csv', '.js', '.pdf', '.html'
- Eml & playbooks files will only be tested for indicators using regex
- Base64 strings of very big length will be ignored automatically
- If PDF file parsing fails, a warning will be issued under the commit message and file will be skipped.


**White Listing**

- If a python file is detected, a related yml file will automatically be pulled and it's context paths will be used as temporary white list.
- Currently regex is being used also in order to identify strings that have high risk of being high entropy strings,
such as dates and UUID, and are regarded as false positives. Also regex is being used to catch and remove patterns that have extremely high probability of being false positives.
