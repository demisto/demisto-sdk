import os
import re
from enum import Enum
from functools import reduce
from typing import Iterable, List, Optional

import click
from demisto_sdk.commands.common.git_util import GitUtil
# dirs
from git import InvalidGitRepositoryError

CAN_START_WITH_DOT_SLASH = '(?:./)?'
NOT_TEST = '(?!Test)'
INTEGRATIONS_DIR = 'Integrations'
SCRIPTS_DIR = 'Scripts'
PLAYBOOKS_DIR = 'Playbooks'
TEST_PLAYBOOKS_DIR = 'TestPlaybooks'
REPORTS_DIR = 'Reports'
DASHBOARDS_DIR = 'Dashboards'
WIDGETS_DIR = 'Widgets'
INCIDENT_FIELDS_DIR = 'IncidentFields'
INCIDENT_TYPES_DIR = 'IncidentTypes'
INDICATOR_FIELDS_DIR = 'IndicatorFields'
INDICATOR_TYPES_DIR = 'IndicatorTypes'
LAYOUTS_DIR = 'Layouts'
CLASSIFIERS_DIR = 'Classifiers'
MAPPERS_DIR = 'Classifiers'
CONNECTIONS_DIR = 'Connections'
PACKS_DIR = 'Packs'
TOOLS_DIR = 'Tools'
RELEASE_NOTES_DIR = 'ReleaseNotes'
TESTS_DIR = 'Tests'
DOC_FILES_DIR = 'doc_files'
DOCUMENTATION_DIR = 'Documentation'

SCRIPT = 'script'
AUTOMATION = 'automation'
INTEGRATION = 'integration'
PLAYBOOK = 'playbook'
TEST_PLAYBOOK = 'testplaybook'
LAYOUT = 'layout'
LAYOUTS_CONTAINER = 'layoutscontainer'
INCIDENT_TYPE = 'incidenttype'
INCIDENT_FIELD = 'incidentfield'
INDICATOR_FIELD = 'indicatorfield'
CONNECTION = 'connection'
CLASSIFIER = 'classifier'
DASHBOARD = 'dashboard'
REPORT = 'report'
INDICATOR_TYPE = 'reputation'
OLD_INDICATOR_TYPE = 'reputations'
WIDGET = 'widget'
TOOL = 'tools'
BETA_INTEGRATION = 'betaintegration'
DOCUMENTATION = 'doc'
MAPPER = 'classifier-mapper'
CANVAS = 'canvas'
OLD_REPUTATION = 'reputations.json'


class FileType(Enum):
    INTEGRATION = 'integration'
    SCRIPT = 'script'
    TEST_SCRIPT = 'testscript'
    PLAYBOOK = 'playbook'
    TEST_PLAYBOOK = 'testplaybook'
    BETA_INTEGRATION = 'betaintegration'
    INCIDENT_FIELD = 'incidentfield'
    INDICATOR_FIELD = 'indicatorfield'
    REPUTATION = 'reputation'
    LAYOUT = 'layout'
    LAYOUTS_CONTAINER = 'layoutscontainer'
    DASHBOARD = 'dashboard'
    INCIDENT_TYPE = 'incidenttype'
    MAPPER = 'mapper'
    OLD_CLASSIFIER = 'classifier_5_9_9'
    CLASSIFIER = 'classifier'
    WIDGET = 'widget'
    REPORT = 'report'
    CONNECTION = 'canvas-context-connections'
    README = 'readme'
    RELEASE_NOTES = 'releasenotes'
    DESCRIPTION = 'description'
    CHANGELOG = 'changelog'
    IMAGE = 'image'
    DOC_IMAGE = 'doc_image'
    PYTHON_FILE = 'pythonfile'
    JAVASCRIPT_FILE = 'javascriptfile'
    POWERSHELL_FILE = 'powershellfile'
    CONF_JSON = 'confjson'
    METADATA = 'metadata'
    WHITE_LIST = 'whitelist'
    LANDING_PAGE_SECTIONS_JSON = 'landingPage_sections.json'
    CONTRIBUTORS = 'contributors'


RN_HEADER_BY_FILE_TYPE = {
    FileType.PLAYBOOK: 'Playbooks',
    FileType.INTEGRATION: 'Integrations',
    FileType.BETA_INTEGRATION: 'Integrations',
    FileType.SCRIPT: 'Scripts',
    FileType.INCIDENT_FIELD: 'Incident Fields',
    FileType.INDICATOR_FIELD: 'Indicator Fields',
    FileType.REPUTATION: 'Indicator Types',
    FileType.INCIDENT_TYPE: 'Incident Types',
    FileType.CLASSIFIER: 'Classifiers',
    FileType.OLD_CLASSIFIER: 'Classifiers',
    FileType.LAYOUTS_CONTAINER: 'Layouts',
    FileType.LAYOUT: 'Layouts',
    FileType.REPORT: 'Reports',
    FileType.WIDGET: 'Widgets',
    FileType.DASHBOARD: 'Dashboards',
    FileType.CONNECTION: 'Connections',
    FileType.MAPPER: 'Mappers',
}

ENTITY_TYPE_TO_DIR = {
    FileType.INTEGRATION.value: INTEGRATIONS_DIR,
    FileType.PLAYBOOK.value: PLAYBOOKS_DIR,
    FileType.SCRIPT.value: SCRIPTS_DIR,
    AUTOMATION: SCRIPTS_DIR,
    FileType.LAYOUT.value: LAYOUTS_DIR,
    FileType.LAYOUTS_CONTAINER.value: LAYOUTS_DIR,
    FileType.INCIDENT_FIELD.value: INCIDENT_FIELDS_DIR,
    FileType.INCIDENT_TYPE.value: INCIDENT_TYPES_DIR,
    FileType.INDICATOR_FIELD.value: INDICATOR_FIELDS_DIR,
    FileType.CONNECTION.value: CONNECTIONS_DIR,
    FileType.CLASSIFIER.value: CLASSIFIERS_DIR,
    FileType.DASHBOARD.value: DASHBOARDS_DIR,
    FileType.REPUTATION.value: INDICATOR_TYPES_DIR,
    FileType.REPORT.value: REPORTS_DIR,
    FileType.WIDGET.value: WIDGETS_DIR,
    FileType.BETA_INTEGRATION.value: INTEGRATIONS_DIR,
    FileType.MAPPER.value: CLASSIFIERS_DIR
}

CONTENT_FILE_ENDINGS = ['py', 'yml', 'png', 'json', 'md']

CUSTOM_CONTENT_FILE_ENDINGS = ['yml', 'json']

CONTENT_ENTITIES_DIRS = [
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PLAYBOOKS_DIR,
    TEST_PLAYBOOKS_DIR,
    REPORTS_DIR,
    DASHBOARDS_DIR,
    WIDGETS_DIR,
    INCIDENT_FIELDS_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INCIDENT_TYPES_DIR,
    LAYOUTS_DIR,
    CLASSIFIERS_DIR,
    CONNECTIONS_DIR
]

CONTENT_ENTITY_UPLOAD_ORDER = [
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PLAYBOOKS_DIR,
    TEST_PLAYBOOKS_DIR,
    INCIDENT_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    CLASSIFIERS_DIR,
    WIDGETS_DIR,
    LAYOUTS_DIR,
    DASHBOARDS_DIR
]

DEFAULT_IMAGE_PREFIX = 'data:image/png;base64,'
DEFAULT_IMAGE_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAMAAAC5zwKfAAACYVBMVEVHcEwAT4UAT4UAT4YAf/8A//8AT4UAf78AT4U' \
                       'AT4UAT4UAUYcAT4YAT4YAT48AXIsAT4UAT4UAUIUAUIUAT4UAT4UAVaoAW5EAUIYAWYwAT4UAT4UAT4UAUIgAT4YAUo' \
                       'UAUIYAUIUAT4YAVY0AUIUAT4UAUIUAUocAUYUAT4UAT4UAT4UAUIYAT4UAUIUAT4cAUYUAUIUAUIYAUocAT4UAUIUAT' \
                       '4YAUY4AUIUAUIYAT4UAVYgAT4UAT4UAT4YAVYUAT4UAT4UAT4YAT4cAT4UAT4UAUYYAZpkAWIUAT4UAT4gAbZEAT4UA' \
                       'UIYAT4UAUIUAT4cAUYgAT4UAZpkAT4UAT4UAT4UAVaoAUIUAT4UAWIkAT4UAU4kAUIUAUIUAU4gAT4UAT4UAT4UAVYg' \
                       'AUIUAT4YAVYkAUYUAT4UAU4cAUIYAUIUAT4gAUIYAVYsAT4YAUocAUYUAUIYAUYgAT4UAT4UAT4UAT4UAUYUAU4UAUY' \
                       'gAT4UAVY0AUIUAUIUAT4UAT4cAT4oAVY0AUYcAUIcAUIUAUIYAUIcAUYcAUIUAT4UAT4UAUIUAT4UAX58AT4UAUIUAU' \
                       'IYAT4UAUIYAUIgAT4UAT4UAUIUAT4UAUIUAT4YAT4UAUIYAT4YAUYkAT4UAUYYAUIUAT4UAT4YAT4YAT4YAT4cAUokA' \
                       'T4UAT4YAUIUAT4UAT4YAUIUAT4UAUIoAT4YAT4UAT4UAT4UAT4UAUIUAT4UAT4YAT4UAUYYAT4YAUYUAT4UAT4YAT4U' \
                       'AUoUAT4UAT4UAUIYAT4YAUIcAYokAT4UAT4UA65kA0ZYAu5PCXoiOAAAAx3RSTlMA+nO6AgG5BP799i9wShAL9/uVzN' \
                       'rxAw6JFLv08EmWKLyPmhI/x88+ccjz4WjtmU1F76VEoFbXGdKMrh71+K0qoZODIMuzSAoXni0H4HnjfnccQwXDjT0Gi' \
                       '/wa5zSCaSvBsWMPb9EnLMoxe3hHOSG+Ilh/S1BnzvJULjimCayy6UAwG1VPta91UVLNgJvZCNBcRuVsPIbb37BllNjC' \
                       'fTLsbrjukKejYCVtqb/5aqiXI9W0tnad4utdt2HEa1ro5EHWpBOBYg3JeEoS2QAAA5lJREFUGBmtwQN7Y0sABuAvbZK' \
                       'T1Ha3tt2ubdu2vXu517Zt27a+TH/VbXgmaTIz53nyvtDaV1+JdDrxHVvzkD43D5BsyUe6bKxmUP0qJNM2Y/Pxud9bMH' \
                       'd5DsNmlmGa/E8ZsvgumHqikFHzPUhgVTGipBxmun20LUCCw4zZAiPtjPMs4r3MmGvbYGA9E6yD7CwlN0FvPac5CckDl' \
                       'LRBK4dJPAxbDiXvQ+c9H5OZQMwW2lZDJ7eQyQ1vQsR+2j6ARnYnU6nKQ8gdtA1Co6mLqXX1AXBf72GUa6EbGmuotCvT' \
                       'u4tRBcOfQ+sATQ2cqoSBF2go6xiMtNNQA8zkH6GZ0zBU/mLFYEcBtbbCiVtrM6lxEA6NVFOpHk6d9lPpbjjVSKWCvXB' \
                       'oHzUyFyG1vuFzM3Yi3rfUqL5/E5Jzv8spz+chjpdao7VIag9D3kAcLw14szHd7h0MGfVAVkITvj/PI4H1OCNyITlPQ6' \
                       '7eDYjTzqirFmy9NDZnwRhsy0sZsw4xzX46kDVRiahHaPNleBD2+wDJSSGZpNK1v8sRstJP2StDFoDsXh+niIBEUOM/h' \
                       'NzLBDWtD/UwTAQkghr/IGgrFURAIqg2WoagzVQQAYmg2nUELaWKCEgEla56EFRMFRGQCCpdQtBlKomARFClA0GecSqJ' \
                       'gERQZSOCLlBNBCSCCucQZJVQTQQkggpnEHSFGiIgEQx76nhrDRPch5BiaoiARHCKv6gOgNW/n7LCOoT8e7GUSpNCMkm' \
                       'y5xmEeTJ8tBUh6q+K2XTA34yYPYx5qxK25Q0FNFYEmzXOqJ8RZ2eRi2Z8syDpY8RiNxIsmu+niSOQuR9liCsb0638ig' \
                       'a+RJwMhpxCUv1fUGsJ4jSt5ZRGpGBldFKjBPHOznjzmyGkNusHahyFQ1eyqPQZnHqQSv4n4VQVlTovwKGD1Mi89Bica' \
                       'KZWVsstFd35MLSUZoqXwcxLNJQBI699TENzYWDs4mya+hBadYOFjFp9YMlaKuVAw5rYwagb93gA1HYxtefKoeaeyRjf' \
                       'GYTkeZlK6TxofE2bFxHWCibn6oeG+zfatiOmgsn4foHOPEqehu1VJrEXWkOU5EKyhtPkQO9OSjZAdpIJDsOAVcOYccR' \
                       'bSJnvExjZzphuJGigzf8jzBz6gxG3u5HAs4JRrhGYGmthkK9xFaYpu41hWbkwVzbyTsdHb59AMtsyGVTahnRZ9hPJ13' \
                       'cjfQ4V89djSKcm71Ho/A9KDXs8/9v7cAAAAABJRU5ErkJggg=='
DEFAULT_DBOT_IMAGE_BASE64 = 'iVBORw0KGgoAAAANSUhEUgAAAEIAAABlCAYAAAD5/TVmAAAfJElEQVR4nNWceZxUxbX4v1X39jLdPQszI8uwCI' \
                            'iAiEuICyIxqHHFLT41MeLPZ4zRaDT5PWPM+vxEf3n56UtiTJTkPde4xaiJcU/QoA9QEYEgAUTWYWT2raf3vkvV' \
                            '+6N7hu6e7p4ehLzf73w+d+7tulV1zzl16tSpc06N4H8Ifrnq5LmNoWm/agwcvlBpu6s9uvFnu7bv/eWdl693Ku' \
                            'xCAupA4WMeqI5GA/euXFBvmOLJOv+hR0+qOR5XpZu6Ex/9+/hpgQ7gqQq7OWBMgH2MkKNsp9g3IsXu5dpgmPIE' \
                            'BHObB1awN7IGhYurLAlcdfQpDU9vXNE7rE2J36XKRg2DjNgf7qoR7qXaZJDWoNHYOjn0Umshx4zzFvZf7rlcGQ' \
                            'wfpJLlMuc6mJA3qgMRuTaVklu1zhRoIG0J1dsnf/dfz7YrRia8sM9SUGpwhpUPcuSAzrcyCAHI75+1oqerR17V' \
                            '2Wmu7+w06Wg3+7q6zR81f5h8IgevQig2JQ4YiAPZWQ6U0+gSUNIQnH/pRQu0I1cieKx2XvM1j393nSrTvpROGg' \
                            '0OuWV5/ZgMV0aVdDwSMmUQEJx73ue9SjPFSciZ2feNyc2zjv7hvQt7phzu6/jq4n9XWutCvEaL20hMy50e8mBJ' \
                            'RB48818/lEJ46l//w+7T2ppjF0opFpmGUaM1Xsu2vYYhldfjsTTaCtR5wtNm1q499jMT/hKq8fzZVXrvOUfeer' \
                            'CnbtGpMaKGLVM3t5zDZjep//zT/55umsaN776x97J3l7VO8nk8eDyZxUophe24SCnxmAYAWoNl20yaEeSCq2aF' \
                            'DUO8nHK496G7X1z/zMNvFVtOC3HMfTfSkj5U76BJxPKtPw0ZprwBuAUY+9rvd7Dtb/1U+X0AaK3RQM4fhNiHjv' \
                            'QqvnzbMRimBIi5micsl9u/uvj/drXs7Drg+BqD3yUjHTr7rIvULVc+2JZQTRXLNt09QxriceA6IAjQNDVIf6SH' \
                            'gf40ibhD2rJJW1b2nrks28bVDrWTExy32EtNvR9T+BBCeKXgOI9k8TmXL9y47e979rbu6RFl8ClGR265yMUZDv' \
                            'CqUVcf4oX37jgWwbPADABXp+lPtRBO7SHtxEglINLhIdZjkopKXFsgDfAEFKEGh5pxDlW1LtLQCGHgM0KM8U2l' \
                            'zj8ZQ3gB+lKuuObt19a9eMc3nzhgukOwb/7kzjdyymSJ58G6CmDM4Yfy7Ms3H+sxxAvAFKVd+tPN9CS2Y6tEzu' \
                            'eKDeIIGGrwGAHGVs2mzj8ZgRGxXX3Vv97y+xffeXlNLm4j0VBYd+h+oCRCLt/287FC8rqEuZYboy22gZjTndF+' \
                            'BwwE1d5xNAWPxWMEejSctWjGv6w/ED3LgudC7TqS+S0BXlhzh6mFuFfC3Jjdxa6BlcTsroqYMDo2aaJWB7sHVh' \
                            'C3exq15qFn199VP6ouioMcyWgZyZBRk2dNpHpM9UWm0BdFrQ72RtfgqGSZJvmwPyJpqQQfR98j4XQd3VDtufWG' \
                            'X3zlE++XKsGjrCm7fPvP66TgvYTdPbMlshpX2wXdlx5z1xa4lkApgZAa06sxPHrEdoNgCi+Tak6K+Y0xJ54+81' \
                            'tbRsC5UL/lvSvmmClmrpYmRotLlI7PbI2tL2ACZPfaaMCKSyJdHuLdHhJ9XpIDHpykiXYlOssIYSo8VQ6BeotA' \
                            'g0XtBItQo4Nh6qJD5miL9tj60PjQ/G8s/sap171y75uDr0azVQdQn0hZ/nHt3f4xteL9j6PvzY1aHRnSlSDaZd' \
                            'LX4ife4yUdNUlliZbCQFaonzWgXAWGQ/CQNKGxaYINNtXjLKoPsRE5EyHoGReu9cw55vNH39myv7TkeqhGvSaH' \
                            'qj0nDKT3zIxanQC4jmDrX2vo3VaLgSfPUjSNUr0UBwEYhgS8pLq9pLqr6dYahUPtoQPMOWsA05eZPgmnuy7lbj' \
                            'gPWDpaGgah3LwpC6dedAKC+IXdyQ+9g/O5fbOfrs21mMKLEAIpJE0TJuD3+ZgwYQJer5cJE8YTCARobGwY1mcw' \
                            'GKShoYG6ujpqaqqprx9DKBRi3Lix+Hw+hBAYwkP/zjp2vRccaqe1wlX9n//VOwv32wdbbJxKmdJ5cM9TX/dH1c' \
                            '7bY1bnxMGyPeuDWP2hIfGvravlttu+xcBAhGuv/TItLR9zw9euI5VOcc7ZZ/HOu6vz+ly06BROP/1UZhw2nYkT' \
                            'J3LCCcfRUF/PxRdfRE9PLx0dmeknpcCyHCYemcqdInVC8PCrD7bER0PHYL1iHKzI5+Cae+qj6dY5ud8SEhKpFB' \
                            '7TxGMaRAYiPPrbx2lubmZgYICdu3bz8CO/paO9g927m4d9eN26v7Fjx05s28a2Hfw+L4lkkm3bd9Da2obWGqU1' \
                            'tu0gVebLORqnXmvmAIM7skqkvKTPMve5cCueB12JrVNtNxHKRaV2go2rFKm0RTSeBMPg8su/wOEzZ3LllVcwaf' \
                            'Ikliy5nLlHHcn55y1GKZ25tEZrzbHHHs2555zNaact4sQTj+dznzudeZ/6FF/4wqVMmjSJWCJJLJ4klbaonWAj' \
                            'jfwBF4KjKyA+F4Zo3O9V4/7VC/8ZeCS3zE5L1j1TR9/HQ55ovF4vjmNjmia27eAxTVzlIqWBbduIQZNBgJSZVU' \
                            'XrzDZdCoHSGiklruugVIbwuiabT18SxhdyC9FaeuP8VTfuDz2jUS55U0Qpxmfs0kFeajw+xbyLwzSvC9K900u0' \
                            'y4NlWQBYVsbGsOzM3c0SNWSFa3BdF3eINoFLxn5wXRchINTgMGFOikM/ncAbGC75WjN+FPTkwWgYkfdl2xGmz6' \
                            'sp1EfeoGLmKVFmnCywEpKBdg/hVg8DHR7ivQZOWuLYZbYhAgxDY/oUwQaH2iabugk2NeMc/NVu1vIsDrYr9nvV' \
                            '2G+JSKSElWFEicqGxl/t4q92GTczBWRM6lTUIBWRmXtM4loCrQXS1Hj9Cl9IUVXrUlXrFh31cmBbIlUC55Hu+y' \
                            '8RkZjsqAlqDKPy/aPh0QTrHYIHYr9YCBoicVnow6s4GicL7oXPJSGRFJv6I/LAepeLqW5R/F1h1WhCEomLv+UU' \
                            'lVsRh7kbii2VFRHnOHprd7+xuqPHxLLF6PwvpeoWK9fF3w36fB1X0Bs2aOs2O1yHZTlViklBSQnJdd7qIs+5kF' \
                            'dn7Z+areM/P219Mi0WhKPGuERS4DgC0wRjpH2FKL9u9+/1EqgpPR6uKwhHJT1hg64+k2hctmnN9csf2Pp+z55Y' \
                            'btVcJ26ek7mQtkriGmXfXf/bRfWGKc8DLgUW+H267tAJjszTHZW6KrP1/vZ8HUeeHcFbpYa900Brp6kiMRkDNq' \
                            'D1C66jn3vlZxtbPv57XyGugzCSW2GIEfu1+8wFf8jDl3+9sEZIcWsoqH4wcayDUUTbuLZACJDmcM7EekxaN1Xx' \
                            '8YYq6qdYzD41RnCMs292aOjqM+gbMJ5zLHXT2uebu9a+0FzMcVsuIDUIeY7ekSzLUe9Or390UcDwykdCVeqypr' \
                            'EuZsGq4tqCPesC2ElJVW3GekpGDAbaTFJRg4apFlM+lcD0aYQAf42bZYKgs0fSHzXWa83i+69Y3lEB7qUidlDA' \
                            'rIMS6brxydNrQD/i9eiLxze6hIrYA4mwwUCbBzslMbyaQJ1D7XinqKSk0oKOHoNESq4XcOl9VyzfdaBxrkQiRh' \
                            't6B+D6RxfVSI+8yxB8pTqkzMY6l3IGWDFwHEHvgCQcNXBdlmnNNUuXLN87ii4qxv+gRsOvvn+hDNR5nwcuEEAw' \
                            'oKgJKQJ+jWnofRoqe9c6Q3zKEkTjkkhcojJkNGulj1h65ZuFluMBg9z8iJH0gATUuKY6AsEg/T1JtMpsijweL+' \
                            'lUUnp9fqVcl2QqIQH++L3NasnSealMthTEEpJYQmJIME2NaYCUGgEolbEJHFfgusMWGWfDy61OIBCUpsej6sbU' \
                            '093ZIaVhgNZUBYIKIJGIy0DIq0I1Hpq3d5ZzQg9TqBVLxILTZ/OjpV86VsN16aTb2NueYteWCHs+itLblUKXYG' \
                            'P1NGt+3WHuJE+1izZcEBothnJGhoMGtERogVASN2EQbTFi/Vt8y3SJwaqt9zJ5RojD5tYyblIVVSEjIYR4cs+O' \
                            '7je+svhXFSn63OVzEIrFOHlt8+31HtNYqWFObgfJmEPn3iQ7N0do3hohGi506YPhgcAYQfV4CDSA4dMZGREFbn' \
                            'otEFqgHEGyH2IdgniPxk4P1y3+gMGUw6s5bG4NTVODhGo9iHzGhrXSnznziNu3UHwZzdt8lUovHMZFw5RzbJWe' \
                            'o7QNSKQwMIRJVchk6uxqps6uRrlN9HSk+Hh7jLbmBL2dSRJRF9tyiXZpol0Zd543KPAFJaZ/nxWqXHAssOKadE' \
                            'xndIMenHqSqpBJXaOXCYcGmDwjxPgpAUzPvvHTKBxlo7WLRiGEUWcI3+eATcO4WMTELmlQ/X7Vt80xjaF5oENS' \
                            'SAbSbSf0pLb9xFFW1kNtYgoffrOWgFlPlaceU2Q9U1kr0LYU/R02nS020X6bRNwmnXKwLBfXVrhKZ/QMmSQRaQ' \
                            'gMQ+D1Gfj8JlUBD8EaD2Mne2ho8uAP5NvuSjsknTAJp4+UE8ZWSZR20FohhUGtb/KjDb4Zj4uMVnYi4eT6fzrx' \
                            'JzGK2BRFGbHwjCO4/b7L7wVuGKwct3toja0vsTMVCCQ+M0TArMdv1uEzghjCixAGWgmSEYj3a5w0gytB3kZN5D' \
                            'wIAaYXArUQqBNIQ6NRuNrCUcks8f2knIGsBBRflhuqZqgG//QhvgEr+ntjZ1224O5h+d5FleUb2+7wJ51Ie3+q' \
                            'uU7pTBtXWaTcSAk2DN9KSGFgykzGi8eowpR+DLwo24OTMnFSEmXLTNwTQGoMU2P4XDx+F+m1UcLCUWlslcBRaR' \
                            'yVwtWV5qyDRwbwGoEsjpIaX5MTNA85/szZt2+gYPCLOmYc1x3fEd8UsNxYRRumYq+VdrHcOBZxGMI905kwBVST' \
                            '3USJbKnORsZ0ZgVKleo5r6uy5bZK5CSpQMLpl03BY6YAGyhQBUUZ0Z3cguXGS1NZMVaFkHXYDm4j9/3KPI3GqT' \
                            'Ean0YWlHboSnxYdHoXLYxY7XJ0KRwHMivmYILGcmNFcymKSkRPv6EaxwyLGewXKAXhqIHlsF/8Mk2oq1b7drH7' \
                            'kYaVCylLOhQxD4oyorNXquqgGvUmqRA00Nc5Bk/HUdS4gUwcpwwhWmRsrAxkKrrSpnfMhxxyaFvGsfgJUFJK0N' \
                            '5tOFQqEckOs6evRlsTxjreYu8r/rBjEOo8Dk96eOR7NODrCeGOex0ZSIxcuQxEYlL17fHGKOPFzoOuFbXz2z/y' \
                            '+ePJT5SWhFRePG4wr0wAUsqilxDFtz6G8mEW9DNasB1Be4vH7FpVc+ERRx49skScdsa5Eri2f3OV+fF4m8mTHI' \
                            'JVFe1bhkExsqprazj99FMzcySbhjw4W1LJFBs/2EhbW3tFfZcJluW9S1uC1g6T7o1VaJdLpk+fedeHmzfmxUCG' \
                            'McLvr5oKfC7db9K1NogmTm2tor7WxevJ+hBG5cUQeYh5PB4mTsqkVOzd28qkSRPzak+aNJGnf/cMsVgsJ6o6/I' \
                            'PlVIUmk8JkuxCOSsIDBr1bqoi3+ACmIDgTeCK3TS4jMk5MIS4G0YjWxHb7cBMS+4REVzgmGz2Glg11GaaMQHte' \
                            '8kIe0tkfWmveWfUuU6cdimmaGIbBUUfPxV/lp2liE9s+2lac2JFWDZHxe3R0G9iOwHVER//6QH10t8+b0+7aw2' \
                            'bMemrnjo8gJz9iENRZ514kgatyv5Ts9IR71gTOR3OF7Yg/JdPCKs+FHGKVxnGc/L2AGLwJUqkka957n3feeZeV' \
                            'K1eRTqeBbO5UDhMzKQEqr+9y37YsoSxbrNCaG52YPD66y7e2oN38WUfMnU0pE9s0zYXk+BuyzH9r08oda//wwO' \
                            'Y1wNPf/uOiD6CyhIy0bfPumvepMuqoq62htqYGf5U/i6/OSwkYjFwBpFJpenr7iESihCMRBiIDfHpKlDG1lXwV' \
                            'bJuIcvXnf/2/3gwDavEFlzwkYEEOL7xCiKura2pvjUYGIDfP8vBZcyRwJTlSkm34yEdbNw9xznZEs1IcLStYUD' \
                            'IuOEVfNExfOAzAQGxfJGrdBxvp7c2c8dQarvrnJVRRxa7mPazf8PchSRKjXLzStgj37IlF2DfiL2roA3LDzxd8' \
                            '5rOf+8mrL/2hD1BDnzh81hFNwLkFfTa7jvNGboGrxBbLrjxXshCUUkPLZDyRJBKNEYnGiMZiQ3sNpXXJrfVIml' \
                            'opsGyx7dkfvj80eLt3busD/lhQdYZALBr8McQIgTgThmWcPLN50wd5nmPX5e9pqzJGFNNrSmni8TiJRAKt8pfl' \
                            '/D1XqW+UVxKWLXBdsYmc+b9l80YF/A6w9p1ZERLBFYN1TICjjvm0BK4t6DMG+smPW3YXGhHrEylp1VariqzOQn' \
                            'I6elq49e4vAqDEWM44/VQgk2sVDGZ8BxnJyCW4crs6kRK4ircp8Lsq5b4jpbEJ9Lyc6uede/7Fk1596Y97TYBz' \
                            'zz5nXjqdPq6qqor+cJi2jk5c111r286Wgu/gOrotmRbNSjFzJD0xJN45ouGrdpl7bhg0tP/1SG6+6Wv5bbRmz5' \
                            '7CTOLKp2IiJRMU8Te89vLzqcUXXPJ7r9czb/LEiYypqyWVSnsj0egXJzZN/Kn5y1/ctyAUCj0//bBpZqAqwK7d' \
                            'u9m2bTubPvzo8WeefmyYO8hJu5GUx1ydtsTMKv/IHpvc1QAyTtpE2AAtSKdtOjo7h+qm02lefW0ZO3ftrojwQl' \
                            'CuIJkSW9C6aFx0+qFTXp0wftxddbW1fGresWitaWtt++HcI2ZvMoGfjJ8wbmwgECAWjTEQHqCutpaTTzy+7pmn' \
                            'HxvW2YNfXcGNT572eiQul1T53bIyIaQodLGT6DNZ9WBjFvG93PzNbw+9cxwH2x4eDhAVWrPxpMB2xFvP3b52UK' \
                            '/lue0PP2z6BZDJ0uvq7GLc+HFMaJpQ09fXf6cJLNi9czctzS3ZND6R/bg4Gfh5sQ9qxRvRuAwfMkbVS1laKgJB' \
                            'L7VjgnTFcv8jADhDylaRTI58yCUQ9FFXFwDK23LhmLSAlzp3RkplxnwaMh7z1r2ttLa2IRDYjj3PBPpcpcZqYN' \
                            'r0aQhgx46dAD2UCKK+8ZstHWfeOGdFLCEuqgmVZoQSac665HBWvthBuC9esl45qAr4OPmsQ3FqVmCVsezTliCZ' \
                            'lM3JAWtNTnFhIKcNoLa2lslTJrFj+04SiQRAmwn8BviB1lp2dXaRTCZxlcK27ScpEWLb9nYHZ9ww56H+iHFBdV' \
                            'DJErtntFbEqt/lgutOwisqNAsLwNFJ2hNrSVjlGdkfMXAVjz98w6pBsckdxOzKoR8A/dVwOOy1bXswGdYB7jGB' \
                            'u2Kx+HSvz7tERSLEE0l27m6ms7vbX/CtPOmwU+6KhDC2xJJybnWZfMi0E2VHOJvj9QndbKXAsgUDURlWrn6K4d' \
                            'MBskvpsjff6jukoYHpU6dgWRaWbRMeGFjm93iWmjd/8+uJ8y685H7TNL8kpZSO4+Jm8oDPgWFZakPMeO/ZXZGF' \
                            'Vx7+H919xr1Bv5bldMUQHCQfb3efgat4bqAr2VyiSibiLcRpPX193r5wGENKlNa4rvvCKy8+l5IAqVRqvW07Pe' \
                            'm0NcgEgNPOPPeCQqkY4vIHf/4YAU+k02JHX0T+j/mxYwlJNC4jwD1PfWt1SdE878JLARYD2cP5Dq7rOsAbkBWZ' \
                            'N/7yskX+6APMMA3PHMrAg9evDGu4szdsqFT6H/IfGPLAcTIpRUrz4Pt/2l1o/MmCqxGYX1Bn657mXc0UnPt8pa' \
                            'BSQAhx2qFTp1MKUlEbrXjOdVnW1mViO/84ZigF7T0Gli22oblrzbPDjDCVd2mOA5oK6ry8aeN6Re7uU2u9msyS' \
                            'mQvnT51+eNl87aVXLk9pzS1pS3S0dZk5xwwOHmgNnb0m0bhMALe8es/Gsv9HYcbMI6RGn0++/8VB69cGfwwxwr' \
                            'LSe4G1BX3MD4WqC7k4DJYuWb4FuCmeFKm9nQdXMpSCjh6TbB74XS0bel/eva5w/PJh1uw5fuC8guJdSquNgz+G' \
                            'Eg527dzGzFlzQsB5vpBi1skORyzwGdNP7p944U1Nm/o70z17t5Vey2eePG6rP+RxbEcsSiSl9Ps0ngP8f89sR9' \
                            'DW5SESkwp4zEo43/vdd9aUDI9PnhXixy8d3zTtuNT3m6YFzm6YLIj1u1iZMMWz772z8vlkMqEh/5SfnjlrTlug' \
                            'zr1x8TWHmGcsXMysqcfgeHuPjNvdXzrmlMa3XnmwpbXUR/++bK844rMT3vYFTMtxxSkDsUwujN+ri2bgloNCeV' \
                            'IKBqKS1k6TlCUV8Ggyat/80HUrcyM+w/LJ/8+fjp9imOJNr8+z+LNHLuGo2ccwda7J7h0dKhkR3/lgw9rBfM38' \
                            'jfSWTR+0zT0nsmbSxIko7dIe+4C+5A6Aeo2+/bq7jyhHknrsG++ovr3xnwJf05pwd5/B7lYP3WFjVNNlkBpXZZ' \
                            'LP97R5aO8xcVxhgb7bsdRND1+/MlbQrPCEgTQ84hvADKVsdvYvJ2H3cUh9E8ec5XSh9arc+sOwu3/1wpXAQoHA' \
                            'kD5M6SXlRFCKloGImPWDs1dWlOt4w5OnHi0Q9wKnAFIICPgVwSpNZtpopAQhMn5/rUFpcBxIW5J4UhBPDuVZAm' \
                            'xCc+vqZ3ctW5fJvx4J5C/f+cybhtSnmNKHKf2knQgI0Fp33Th/1bjcyoN5lrkdtwEY0sOcxvOJWd3sCr9Ff8To' \
                            '273Drjhd5eHrV228+r6Tz5emvAi4TWvmxJNSxrObTSkyTlmBzka9MozYR/iQPb4XuFcp/ejTt73X099WcfxT9f' \
                            'TLjrH1LkFPI7MazmZb7zLC6Y8BhvkrhkvEuwsXIXgJRMhjVJG2k4SjkmRa/GLiWOevwK7WHbGt/7ZkQ8VxwCvv' \
                            'OckMNfoXSCkuBRYAU4A6hkfaFBAhMxhr0foP6aT7xoPXrqiY+ruXzfcGq82FCOb1R+RE1xXfHFOj8Hl8KG2jtW' \
                            'tpzdduPGnVw2UZcdsjx8jGqbUXJNPix0oz22tq6fNqfD5tCfACYeC+dMK9819Oe3fkYE8BXPfIIr/hkeOBsULQ' \
                            'iBAhAVKjEyh6gC7l6o7lD3wY+2jVSAn4+fCrt0+ukYb4GbAE8EMmm9eyIZWWKE2L36vvchOpB7933hqLkTJv/d' \
                            'Uefrps/iUC/R8ISh1Fe1kprr3trNUdiWjlCV45sL9nRIa1mzN/DF//xZHTNTxORuLQSmSO7ezbDFpa892l39r6' \
                            '8y1vD7c7ijLi3hULAqZXbgeaNBCNSQZiEinhkDGZYHAW1iqlr7hpwdvbDgRB+9vuvtULjxPwJDATMi67rr6MlV' \
                            'sdVBxSr5CZDJSeVMKddstp7xauOMXzI0yvnAmMBegfMGjtMnuicXnHQERe3dJuPpNIycGV4zgpxV/vX71w0c+X' \
                            'nzTaZIr9PTE01O4HT31K3v/uwosE/IUsEyJx2dfaaX4/kRRHWpY4ozdsrO/uG0Ktxuc3phTrtBTyocGH/ohMob' \
                            'n21Z9t/NH9S5Y/Gh1wr+jsNa5LpsWgApsE/MFXZXxx/uKxlTCj1JHDUu+GHU0EuPSW6XLCtODXETxJNpQXT4qe' \
                            '7j7jn9p2xv5t6ZLlW39z9VtvaM3VkZgRzmlbGI+RpZAhd8a4LpscS728e32PAnjw2hXO3u2Jx7r7jOssWwyKWD' \
                            '2Ch6784czrb77vqJGYUcyDVO7dsDzxxiY/iy5tugzB7UAAIG2Jrp5+4wvP3vHBW89+/30A5dqKrSvaN2n0+pwz' \
                            '7EXzzouOjhAMGU1Ssuk3V7+Vpw2f/s57NG+NPxWJyRuVIgFsBX6ilX6jfVfJ/Ujht8pJxOBzbirg0LuethR7Nk' \
                            'efA04H7lZabIgl5BXP//TDt3JO+kmA5f/5oTIkO7IJGwpEqti3i2bna62HGGEaDFMsAL//7vvqsjvmPXHiZ4Nr' \
                            'TOnufeyO7Yl1r3eXm/elXOyFdQaVYd4pvML6d1/zgQNsWHztlI0nXdD0o2fuaUlsf6cT8pWpBJTHHKRHozXFLO' \
                            'Oi/34J0FaGe+D16pK2wjP/ul49k5GGSqDcMcTcOhTUKatUX3mgRb3yQEuuwTWsnS+HBq1VMXpUUUZohTOYk+Av' \
                            'w4j9hEqk5oBClW+IBoUWRRNOSynLIZ0Q8Kv9i8wMh4NCZCVQ5dPbyYbJhCyOR3FGZBRsDFjqNfVvDg56ZeGTJX' \
                            'gWQH974gngLGCNLmU7FcVCEtGaM1a/0rX+8Tv3x2j8xHBApedHl61zgLfufn3+GdFee7/6LjcyRQ2d/axfaqks' \
                            'VVbYxyd99/80/H+BZCGMBumi5yUq6G+0EliufaEE/sNgJBEv1WY0v0eLT959NAGIYYbQxIkTefXPf5ZVPr/0+r' \
                            'ym3+evkdJodJVbL6WsEUKEyOwFAhq8IuMsMQFPtgszeznsO/llZ58tMie7EkBCaRVDE9FKhTX0KNcNt7a1OR3t' \
                            '7eorX7lGdXd3V4x3MRCUMGFHgvnz5/PiSy+fCdxEJlt3fJboAxb+H6GbFBmX3jbg12MPaXyx4H0xBhRat0N3s0' \
                            'jliiBUXY1lWWs9Hs+PgZlCMAXNBIRoRFMH1JDZzgeyl5/MFthk+FY4FyyyEqEzxKbI2DQxMv7MMJnQZDvovVqz' \
                            'A1HUzK9kdzt0/2+exnQr4g2hrAAAAABJRU5ErkJggg=='
# file types regexes
PIPFILE_REGEX = r'.*/Pipfile(\.lock)?'
TEST_DATA_REGEX = r'.*test_data.*'
TEST_FILES_REGEX = r'.*test_files.*'
DOCS_REGEX = r'.*docs.*'
IMAGE_REGEX = r'.*\.png$'
DESCRIPTION_REGEX = r'.*\.md'
SCHEMA_REGEX = 'Tests/schemas/.*.yml'
CONF_PATH = 'Tests/conf.json'

PACKS_DIR_REGEX = fr'{CAN_START_WITH_DOT_SLASH}{PACKS_DIR}'
PACK_DIR_REGEX = fr'{PACKS_DIR_REGEX}\/([^\\\/]+)'

INTEGRATIONS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{INTEGRATIONS_DIR}'
INTEGRATION_PACKAGE_REGEX = fr'{INTEGRATIONS_DIR_REGEX}\/([^\\/]+)'

PACKS_INTEGRATION_PY_REGEX = fr'{INTEGRATION_PACKAGE_REGEX}\/\2\.py'
PACKS_INTEGRATION_TEST_PY_REGEX = fr'{INTEGRATION_PACKAGE_REGEX}/\2_test\.py'
PACKS_INTEGRATION_PS_REGEX = fr'{INTEGRATION_PACKAGE_REGEX}/\2.ps1$'
PACKS_INTEGRATION_PS_TEST_REGEX = fr'{INTEGRATION_PACKAGE_REGEX}/\2\.Tests\.ps1$'
PACKS_INTEGRATION_YML_REGEX = fr'{INTEGRATION_PACKAGE_REGEX}/\2\.yml'
PACKS_INTEGRATION_README_REGEX = fr'{INTEGRATION_PACKAGE_REGEX}/README.md$'

PACKS_INTEGRATION_NON_SPLIT_BASE_REGEX = fr'{INTEGRATIONS_DIR_REGEX}/integration-([^\\/]+)'
PACKS_INTEGRATION_NON_SPLIT_YML_REGEX = fr'{PACKS_INTEGRATION_NON_SPLIT_BASE_REGEX}\.yml$'
PACKS_INTEGRATION_NON_SPLIT_README_REGEX = fr'{PACKS_INTEGRATION_NON_SPLIT_BASE_REGEX}_README.md$'

SCRIPTS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{SCRIPTS_DIR}'
SCRIPT_DIR_REGEX = fr'{SCRIPTS_DIR_REGEX}\/([^\\/]+)'
SCRIPT_TYPE_REGEX = '.*script-.*.yml'
PACKS_SCRIPT_PY_REGEX = fr'{SCRIPT_DIR_REGEX}/\2\.py'
PACKS_SCRIPT_TEST_PY_REGEX = fr'{SCRIPT_DIR_REGEX}/\2_test\.py'
PACKS_SCRIPT_PS_REGEX = fr'{SCRIPT_DIR_REGEX}/\2.ps1$'
PACKS_SCRIPT_TEST_PS_REGEX = fr'{SCRIPT_DIR_REGEX}/\2\.Tests\.ps1$'
PACKS_SCRIPT_YML_REGEX = fr'{SCRIPT_DIR_REGEX}\/\2\.yml'
PACKS_SCRIPT_README_REGEX = fr'{SCRIPT_DIR_REGEX}/README.md$'

PACKS_SCRIPT_NON_SPLIT_BASE_REGEX = fr'{SCRIPTS_DIR_REGEX}/script-([^\\/]+)'
PACKS_SCRIPT_TEST_PLAYBOOK = fr'{PACK_DIR_REGEX}/{TEST_PLAYBOOKS_DIR}/script-([^\\/]+).yml$'
PACKS_SCRIPT_NON_SPLIT_YML_REGEX = fr'{PACKS_SCRIPT_NON_SPLIT_BASE_REGEX}\.yml$'
PACKS_SCRIPT_NON_SPLIT_README_REGEX = fr'{PACKS_SCRIPT_NON_SPLIT_BASE_REGEX}_README.md$'

PACKS_LAYOUTS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{LAYOUTS_DIR}'
PACKS_LAYOUT_JSON_REGEX = fr'{PACKS_LAYOUTS_DIR_REGEX}\/(?!layoutscontainer)([^/]+)\.json'

PACKS_LAYOUTS_CONTAINER_JSON_REGEX = fr'{PACKS_LAYOUTS_DIR_REGEX}\/layoutscontainer([^/]+)\.json'

PACKS_WIDGETS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{WIDGETS_DIR}'
PACKS_WIDGET_JSON_REGEX = fr'{PACKS_WIDGETS_DIR_REGEX}\/([^/]+)\.json'

PACKS_DASHBOARDS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{DASHBOARDS_DIR}'
PACKS_DASHBOARD_JSON_REGEX = fr'{PACKS_DASHBOARDS_DIR_REGEX}\/([^/]+)\.json'

PACKS_REPORTS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{REPORTS_DIR}'
PACKS_REPORT_JSON_REGEX = fr'{PACKS_REPORTS_DIR_REGEX}\/([^/]+)\.json'

PACKS_INCIDENT_TYPES_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{INCIDENT_TYPES_DIR}'
PACKS_INCIDENT_TYPE_JSON_REGEX = fr'{PACKS_INCIDENT_TYPES_DIR_REGEX}\/([^/]+)\.json'

PACKS_INCIDENT_FIELDS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{INCIDENT_FIELDS_DIR}'
PACKS_INCIDENT_FIELD_JSON_REGEX = fr'{PACKS_INCIDENT_FIELDS_DIR_REGEX}\/([^/]+)\.json'

PACKS_INDICATOR_TYPES_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{INDICATOR_TYPES_DIR}'
PACKS_INDICATOR_TYPE_JSON_REGEX = fr'{PACKS_INDICATOR_TYPES_DIR_REGEX}\/([^/]+)\.json'

PACKS_INDICATOR_FIELDS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{INDICATOR_FIELDS_DIR}'
PACKS_INDICATOR_FIELD_JSON_REGEX = fr'{PACKS_INDICATOR_FIELDS_DIR_REGEX}\/([^/]+)\.json'

PACKS_CLASSIFIERS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{CLASSIFIERS_DIR}'

_PACKS_CLASSIFIER_BASE_REGEX = fr'{PACKS_CLASSIFIERS_DIR_REGEX}\/*classifier-(?!mapper).*(?<!5_9_9)'
PACKS_CLASSIFIER_JSON_REGEX = fr'{_PACKS_CLASSIFIER_BASE_REGEX}\.json'

# old classifier structure
_PACKS_CLASSIFIER_BASE_5_9_9_REGEX = fr'{PACKS_CLASSIFIERS_DIR_REGEX}\/*classifier-(?!mapper).*_5_9_9'
PACKS_CLASSIFIER_JSON_5_9_9_REGEX = fr'{_PACKS_CLASSIFIER_BASE_5_9_9_REGEX}\.json'

_PACKS_MAPPER_BASE_REGEX = fr'{PACKS_CLASSIFIERS_DIR_REGEX}\/classifier-(?=mapper).*'
PACKS_MAPPER_JSON_REGEX = fr'{_PACKS_MAPPER_BASE_REGEX}\.json'

PACKS_CONNECTIONS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{CONNECTIONS_DIR}'
PACKS_CONNECTION_JSON_REGEX = fr'{PACKS_CONNECTIONS_DIR_REGEX}\/canvas-context-connections.*\.json$'

PACKS_RELEASE_NOTES_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{RELEASE_NOTES_DIR}'

PLAYBOOKS_DIR_REGEX = fr'{PACK_DIR_REGEX}\/{PLAYBOOKS_DIR}'
PLAYBOOK_BASE_REGEX = fr'{PLAYBOOKS_DIR_REGEX}\/.*'
PLAYBOOK_YML_REGEX = fr'{PLAYBOOK_BASE_REGEX}\.yml'
PLAYBOOK_README_REGEX = fr'{PLAYBOOK_BASE_REGEX}_README\.md$'

TEST_SCRIPT_REGEX = r'{}{}.*script-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, TEST_PLAYBOOKS_DIR)
TEST_PLAYBOOK_YML_REGEX = fr'{PACK_DIR_REGEX}/{TEST_PLAYBOOKS_DIR}\/(?!script-)([^.]+)\.yml'

PACKS_INDICATOR_TYPES_REPUTATIONS_REGEX = r'{}{}/([^/]+)/{}/reputations.json'.format(CAN_START_WITH_DOT_SLASH,
                                                                                     PACKS_DIR,
                                                                                     INDICATOR_TYPES_DIR)
PACKS_RELEASE_NOTES_REGEX = r'{}{}/([^/]+)/{}/([^/]+)\.md$'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR,
                                                                   RELEASE_NOTES_DIR)
PACKS_TOOLS_REGEX = r'{}{}/([^/]+)/{}/([^.]+)\.zip'.format(CAN_START_WITH_DOT_SLASH, PACKS_DIR, TOOLS_DIR)

PLAYBOOK_REGEX = r'{}(?!Test){}/playbook-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, PLAYBOOKS_DIR)

TEST_PLAYBOOK_REGEX = r'{}{}/(?!script-).*\.yml$'.format(CAN_START_WITH_DOT_SLASH, TEST_PLAYBOOKS_DIR)
TEST_NOT_PLAYBOOK_REGEX = r'{}{}/(?!playbook).*-.*\.yml$'.format(CAN_START_WITH_DOT_SLASH, TEST_PLAYBOOKS_DIR)

CONNECTIONS_REGEX = r'{}{}.*canvas-context-connections.*\.json$'.format(CAN_START_WITH_DOT_SLASH, CONNECTIONS_DIR)

INDICATOR_TYPES_REPUTATIONS_REGEX = r'{}{}.reputations\.json$'.format(CAN_START_WITH_DOT_SLASH, INDICATOR_TYPES_DIR)

# deprecated regex
DEPRECATED_DESC_REGEX = r"Deprecated\.\s*(.*?Use .*? instead\.*?)"
DEPRECATED_NO_REPLACE_DESC_REGEX = r"Deprecated\.\s*(.*?No available replacement\.*?)"

DEPRECATED_REGEXES: List[str] = [
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX
]

PACK_METADATA_NAME = 'name'
PACK_METADATA_DESC = 'description'
PACK_METADATA_SUPPORT = 'support'
PACK_METADATA_MIN_VERSION = 'serverMinVersion'
PACK_METADATA_CURR_VERSION = 'currentVersion'
PACK_METADATA_AUTHOR = 'author'
PACK_METADATA_URL = 'url'
PACK_METADATA_EMAIL = 'email'
PACK_METADATA_CATEGORIES = 'categories'
PACK_METADATA_TAGS = 'tags'
PACK_METADATA_CREATED = 'created'
PACK_METADATA_CERTIFICATION = 'certification'
PACK_METADATA_USE_CASES = 'useCases'
PACK_METADATA_KEYWORDS = 'keywords'
PACK_METADATA_PRICE = 'price'
PACK_METADATA_DEPENDENCIES = 'dependencies'

PACK_METADATA_FIELDS = (PACK_METADATA_NAME, PACK_METADATA_DESC, PACK_METADATA_SUPPORT,
                        PACK_METADATA_CURR_VERSION, PACK_METADATA_AUTHOR, PACK_METADATA_URL, PACK_METADATA_CATEGORIES,
                        PACK_METADATA_TAGS, PACK_METADATA_USE_CASES, PACK_METADATA_KEYWORDS)
API_MODULES_PACK = 'ApiModules'
API_MODULE_PY_REGEX = r'{}{}/{}/{}/([^/]+)/([^.]+)\.py'.format(
    CAN_START_WITH_DOT_SLASH, PACKS_DIR, API_MODULES_PACK, SCRIPTS_DIR)
API_MODULE_YML_REGEX = r'{}{}/{}/{}/([^/]+)/([^.]+)\.yml'.format(
    CAN_START_WITH_DOT_SLASH, PACKS_DIR, API_MODULES_PACK, SCRIPTS_DIR)
API_MODULE_REGEXES = [
    API_MODULE_PY_REGEX,
    API_MODULE_YML_REGEX
]

ID_IN_COMMONFIELDS = [  # entities in which 'id' key is under 'commonfields'
    'integration',
    'script'
]
ID_IN_ROOT = [  # entities in which 'id' key is in the root
    'playbook',
    'dashboard',
    'incident_type',
    'layoutscontainer',
]

INTEGRATION_PREFIX = 'integration'
SCRIPT_PREFIX = 'script'

# Pack Unique Files
PACKS_WHITELIST_FILE_NAME = '.secrets-ignore'
PACKS_PACK_IGNORE_FILE_NAME = '.pack-ignore'
PACKS_PACK_META_FILE_NAME = 'pack_metadata.json'
PACKS_README_FILE_NAME = 'README.md'
PACKS_CONTRIBUTORS_FILE_NAME = 'CONTRIBUTORS.md'

PYTHON_TEST_REGEXES = [
    PACKS_SCRIPT_TEST_PY_REGEX,
    PACKS_INTEGRATION_TEST_PY_REGEX
]

PYTHON_INTEGRATION_REGEXES = [
    PACKS_INTEGRATION_PY_REGEX
]

PLAYBOOKS_REGEXES_LIST = [
    PLAYBOOK_REGEX,
    TEST_PLAYBOOK_REGEX
]

PYTHON_SCRIPT_REGEXES = [
    PACKS_SCRIPT_PY_REGEX
]

PYTHON_ALL_REGEXES: List[str] = sum(
    [
        PYTHON_SCRIPT_REGEXES,
        PYTHON_INTEGRATION_REGEXES,
        PYTHON_TEST_REGEXES
    ], []
)

INTEGRATION_REGXES: List[str] = [
    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX
]

YML_INTEGRATION_REGEXES: List[str] = [
    PACKS_INTEGRATION_YML_REGEX,
    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX
]

YML_ALL_INTEGRATION_REGEXES: List[str] = sum(
    [
        YML_INTEGRATION_REGEXES,
    ], []
)

YML_SCRIPT_REGEXES: List[str] = [
    PACKS_SCRIPT_YML_REGEX,
    PACKS_SCRIPT_NON_SPLIT_YML_REGEX,
    PACKS_SCRIPT_TEST_PLAYBOOK
]

YML_ALL_SCRIPTS_REGEXES: List[str] = sum(
    [
        YML_SCRIPT_REGEXES
    ], []
)

YML_PLAYBOOKS_NO_TESTS_REGEXES: List[str] = [
    PLAYBOOK_YML_REGEX
]

YML_TEST_PLAYBOOKS_REGEXES: List[str] = [
    TEST_PLAYBOOK_YML_REGEX
]

YML_ALL_PLAYBOOKS_REGEX: List[str] = sum(
    [
        YML_PLAYBOOKS_NO_TESTS_REGEXES,
        YML_TEST_PLAYBOOKS_REGEXES,
    ], []
)

YML_ALL_REGEXES: List[str] = sum(
    [
        YML_INTEGRATION_REGEXES,
        YML_SCRIPT_REGEXES,
        YML_PLAYBOOKS_NO_TESTS_REGEXES,
        YML_TEST_PLAYBOOKS_REGEXES
    ], []
)

JSON_INDICATOR_AND_INCIDENT_FIELDS = [
    PACKS_INCIDENT_FIELD_JSON_REGEX,
    PACKS_INDICATOR_FIELD_JSON_REGEX
]

JSON_ALL_WIDGETS_REGEXES = [
    PACKS_WIDGET_JSON_REGEX,
]

JSON_ALL_DASHBOARDS_REGEXES = [
    PACKS_DASHBOARD_JSON_REGEX,
]

JSON_ALL_CLASSIFIER_REGEXES = [
    PACKS_CLASSIFIER_JSON_REGEX,
]

JSON_ALL_CLASSIFIER_REGEXES_5_9_9 = [
    PACKS_CLASSIFIER_JSON_5_9_9_REGEX,
]

JSON_ALL_MAPPER_REGEXES = [
    PACKS_MAPPER_JSON_REGEX,
]

JSON_ALL_LAYOUT_REGEXES = [
    PACKS_LAYOUT_JSON_REGEX,
]

JSON_ALL_LAYOUTS_CONTAINER_REGEXES = [
    PACKS_LAYOUTS_CONTAINER_JSON_REGEX,
]

JSON_ALL_INCIDENT_FIELD_REGEXES = [
    PACKS_INCIDENT_FIELD_JSON_REGEX,
]

JSON_ALL_INCIDENT_TYPES_REGEXES = [
    PACKS_INCIDENT_TYPE_JSON_REGEX,
]

JSON_ALL_INDICATOR_FIELDS_REGEXES = [
    PACKS_INDICATOR_FIELD_JSON_REGEX
]

JSON_ALL_INDICATOR_TYPES_REGEXES = [
    PACKS_INDICATOR_TYPE_JSON_REGEX
]

JSON_ALL_REPUTATIONS_INDICATOR_TYPES_REGEXES = [
    PACKS_INDICATOR_TYPES_REPUTATIONS_REGEX
]

JSON_ALL_CONNECTIONS_REGEXES = [
    CONNECTIONS_REGEX,
]

JSON_ALL_REPORTS_REGEXES = [
    PACKS_REPORT_JSON_REGEX
]

CHECKED_TYPES_REGEXES = [
    # Playbooks
    PLAYBOOK_YML_REGEX,
    TEST_PLAYBOOK_YML_REGEX,

    # Integrations
    PACKS_INTEGRATION_YML_REGEX,
    PACKS_INTEGRATION_PY_REGEX,
    PACKS_INTEGRATION_PS_REGEX,
    PACKS_INTEGRATION_TEST_PY_REGEX,
    PACKS_INTEGRATION_README_REGEX,

    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX,

    # Scripts yaml
    PACKS_SCRIPT_YML_REGEX,
    PACKS_SCRIPT_NON_SPLIT_YML_REGEX,
    PACKS_SCRIPT_PY_REGEX,
    PACKS_SCRIPT_PS_REGEX,
    PACKS_SCRIPT_TEST_PY_REGEX,
    PACKS_SCRIPT_README_REGEX,
    PACKS_SCRIPT_TEST_PLAYBOOK,

    PACKS_CLASSIFIER_JSON_REGEX,
    PACKS_CLASSIFIER_JSON_5_9_9_REGEX,
    PACKS_MAPPER_JSON_REGEX,
    PACKS_DASHBOARD_JSON_REGEX,
    PACKS_INCIDENT_TYPE_JSON_REGEX,
    PACKS_INCIDENT_FIELD_JSON_REGEX,
    PACKS_INDICATOR_FIELD_JSON_REGEX,
    PACKS_INDICATOR_TYPE_JSON_REGEX,
    PACKS_LAYOUT_JSON_REGEX,
    PACKS_LAYOUTS_CONTAINER_JSON_REGEX,
    PACKS_WIDGET_JSON_REGEX,
    PACKS_REPORT_JSON_REGEX,
    PACKS_RELEASE_NOTES_REGEX,
    PACKS_TOOLS_REGEX,
    CONNECTIONS_REGEX,
    # ReleaseNotes
    PACKS_RELEASE_NOTES_REGEX
]

CHECKED_TYPES_NO_REGEX = [item.replace(CAN_START_WITH_DOT_SLASH, "").replace(NOT_TEST, "") for item in
                          CHECKED_TYPES_REGEXES]

PATHS_TO_VALIDATE: List[str] = sum(
    [
        PYTHON_ALL_REGEXES,
        JSON_ALL_REPORTS_REGEXES
    ], []
)

PACKAGE_SCRIPTS_REGEXES = [
    PACKS_SCRIPT_PY_REGEX,
    PACKS_SCRIPT_YML_REGEX
]

PACKAGE_SUPPORTING_DIRECTORIES = [INTEGRATIONS_DIR, SCRIPTS_DIR]

IGNORED_TYPES_REGEXES = [DESCRIPTION_REGEX, IMAGE_REGEX, PIPFILE_REGEX, SCHEMA_REGEX]

IGNORED_PACK_NAMES = ['Legacy', 'NonSupported', 'ApiModules']

PACK_IGNORE_TEST_FLAG = 'auto-test'

PACKAGE_YML_FILE_REGEX = r'(?:\./)?(?:Packs/[^/]+\/)?(?:Integrations|Scripts)\/([^\\/]+)/([^\\/]+)\.yml'

OLD_YML_FORMAT_FILE = [PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, PACKS_SCRIPT_NON_SPLIT_YML_REGEX]

DIR_LIST_FOR_REGULAR_ENTETIES = [
    PLAYBOOKS_DIR,
    REPORTS_DIR,
    DASHBOARDS_DIR,
    WIDGETS_DIR,
    INCIDENT_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    LAYOUTS_DIR,
    CLASSIFIERS_DIR,
    INDICATOR_TYPES_DIR,
    CONNECTIONS_DIR,
    INDICATOR_FIELDS_DIR,
]
PACKS_DIRECTORIES = [
    SCRIPTS_DIR,
    INTEGRATIONS_DIR,
    DASHBOARDS_DIR,
    WIDGETS_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    REPORTS_DIR,
    CONNECTIONS_DIR,
    PLAYBOOKS_DIR
]
SPELLCHECK_FILE_TYPES = [
    PACKS_INTEGRATION_YML_REGEX,
    PACKS_SCRIPT_YML_REGEX,
    PLAYBOOK_YML_REGEX
]

KNOWN_FILE_STATUSES = ['a', 'm', 'd', 'r'] + ['r{:03}'.format(i) for i in range(101)]

CODE_FILES_REGEX = [
    PACKS_INTEGRATION_PY_REGEX,
    PACKS_SCRIPT_PY_REGEX,
    PACKS_INTEGRATION_PS_REGEX,
    PACKS_SCRIPT_PS_REGEX
]

SCRIPTS_REGEX_LIST = [PACKS_SCRIPT_YML_REGEX, PACKS_SCRIPT_PY_REGEX, PACKS_SCRIPT_PS_REGEX]

# All files that have related yml file
REQUIRED_YML_FILE_TYPES = [PACKS_INTEGRATION_PY_REGEX,
                           PACKS_INTEGRATION_README_REGEX,
                           PACKS_INTEGRATION_NON_SPLIT_README_REGEX,

                           PACKS_SCRIPT_PY_REGEX,
                           PACKS_SCRIPT_README_REGEX,
                           PACKS_SCRIPT_NON_SPLIT_README_REGEX,

                           PLAYBOOK_README_REGEX]

TYPE_PWSH = 'powershell'
TYPE_PYTHON = 'python'
TYPE_JS = 'javascript'

TYPE_TO_EXTENSION = {
    TYPE_PYTHON: '.py',
    TYPE_JS: '.js',
    TYPE_PWSH: '.ps1'
}

TESTS_AND_DOC_DIRECTORIES = [
    'testdata',
    'test_data',
    'data_test',
    'tests_data',
    'doc_files'
]

FILE_TYPES_FOR_TESTING = [
    '.py',
    '.js',
    '.yml',
    '.ps1'
]

# python subtypes
PYTHON_SUBTYPES = {'python3', 'python2'}


def urljoin(*args: str):
    """Gets arguments to join as url

    Args:
        *args: args to join

    Returns:
        Joined url

    Examples:
        >>> urljoin('https://www.example.com', 'suffix/', '/suffix2', 'suffix', 'file.json')
        'https://www.example.com/suffix/suffix2/suffix/file.json'
    """
    return reduce(lambda a, b: str(a).rstrip('/') + '/' + str(b).lstrip('/'), args).rstrip("/")


class GithubCredentials:
    ENV_TOKEN_NAME = 'DEMISTO_SDK_GITHUB_TOKEN'
    TOKEN: Optional[str]

    def __init__(self):
        self.TOKEN = os.getenv(self.ENV_TOKEN_NAME)


class GithubContentConfig:
    """Holds links, credentials and other content related github configuration

    Attributes:
        CURRENT_REPOSITORY: The current repository in the cwd
        CONTENT_GITHUB_LINK: Link to the raw content git repository
        CONTENT_GITHUB_MASTER_LINK: Link to the content git repository's master branch
        Credentials: Credentials to the git.
    """
    BASE_RAW_GITHUB_LINK = r'https://raw.githubusercontent.com/'
    SDK_API_GITHUB_RELEASES = r'https://api.github.com/repos/demisto/demisto-sdk/releases'
    OFFICIAL_CONTENT_REPO_NAME = 'demisto/content'
    CONTENT_GITHUB_UPSTREAM = r'upstream.*demisto/content'
    CONTENT_GITHUB_ORIGIN = r'origin.*demisto/content'

    CURRENT_REPOSITORY: str
    CONTENT_GITHUB_LINK: str
    CONTENT_GITHUB_MASTER_LINK: str

    def __init__(self, repo_name: Optional[str] = None):
        if not repo_name:
            try:
                urls = list(GitUtil().repo.remote().urls)
                self.CURRENT_REPOSITORY = self._get_repository_name(urls)
            except (InvalidGitRepositoryError, AttributeError):  # No repository
                self.CURRENT_REPOSITORY = self.OFFICIAL_CONTENT_REPO_NAME
        else:
            self.CURRENT_REPOSITORY = repo_name
        # DO NOT USE os.path.join on URLs, it may cause errors
        self.CONTENT_GITHUB_LINK = urljoin(self.BASE_RAW_GITHUB_LINK, self.CURRENT_REPOSITORY)
        self.CONTENT_GITHUB_MASTER_LINK = urljoin(self.CONTENT_GITHUB_LINK, r'master')
        self.Credentials = GithubCredentials()

    @staticmethod
    def _get_repository_name(urls: Iterable) -> str:
        """Returns the git repository of the cwd.
        if not running in a git repository, will return an empty string
        """
        try:
            for url in urls:
                repo = re.findall(r'.com[/:](.*)', url)[0].replace('.git', '')
                return repo
        except (AttributeError, IndexError):
            pass

        # default to content repo if the repo is not found
        click.secho('Could not find the repository name - defaulting to demisto/content', fg='yellow')
        return GithubContentConfig.OFFICIAL_CONTENT_REPO_NAME


OFFICIAL_CONTENT_ID_SET_PATH = 'https://storage.googleapis.com/marketplace-dist/content/id_set.json'


# Run all test signal
RUN_ALL_TESTS_FORMAT = 'Run all tests'
FILTER_CONF = './artifacts/filter_file.txt'


class PB_Status:
    NOT_SUPPORTED_VERSION = 'Not supported version'
    COMPLETED = 'completed'
    FAILED = 'failed'
    IN_PROGRESS = 'inprogress'
    FAILED_DOCKER_TEST = 'failed_docker_test'


# change log regexes
UNRELEASE_HEADER = '## [Unreleased]\n'  # lgtm[py/regex/duplicate-in-character-class]
CONTENT_RELEASE_TAG_REGEX = r'^\d{2}\.\d{1,2}\.\d'
RELEASE_NOTES_REGEX = re.escape(UNRELEASE_HEADER) + r'([\s\S]+?)## \[\d{2}\.\d{1,2}\.\d\] - \d{4}-\d{2}-\d{2}'

# Beta integration disclaimer
BETA_INTEGRATION_DISCLAIMER = 'Note: This is a beta Integration,' \
                              ' which lets you implement and test pre-release software. ' \
                              'Since the integration is beta, it might contain bugs. ' \
                              'Updates to the integration during the beta phase might include ' \
                              'non-backward compatible features. We appreciate your feedback on ' \
                              'the quality and usability of the integration to help us identify issues, ' \
                              'fix them, and continually improve.'

# Integration categories according to the schema
INTEGRATION_CATEGORIES = ['Analytics & SIEM', 'Utilities', 'Messaging', 'Endpoint', 'Network Security',
                          'Vulnerability Management', 'Case Management', 'Forensics & Malware Analysis',
                          'IT Services', 'Data Enrichment & Threat Intelligence', 'Authentication', 'Database',
                          'Deception', 'Email Gateway', 'Identity and Access Management', 'File Integrity Management']
SCHEMA_TO_REGEX = {
    'integration': YML_INTEGRATION_REGEXES,
    'playbook': YML_ALL_PLAYBOOKS_REGEX,
    'script': YML_SCRIPT_REGEXES,
    'widget': JSON_ALL_WIDGETS_REGEXES,
    'dashboard': JSON_ALL_DASHBOARDS_REGEXES,
    'canvas-context-connections': JSON_ALL_CONNECTIONS_REGEXES,
    'classifier_5_9_9': JSON_ALL_CLASSIFIER_REGEXES_5_9_9,
    'classifier': JSON_ALL_CLASSIFIER_REGEXES,
    'mapper': JSON_ALL_MAPPER_REGEXES,
    'layoutscontainer': JSON_ALL_LAYOUTS_CONTAINER_REGEXES,
    'layout': JSON_ALL_LAYOUT_REGEXES,
    'incidentfield': JSON_ALL_INCIDENT_FIELD_REGEXES + JSON_ALL_INDICATOR_FIELDS_REGEXES,
    'incidenttype': JSON_ALL_INCIDENT_TYPES_REGEXES,
    'image': [IMAGE_REGEX],
    'reputation': JSON_ALL_INDICATOR_TYPES_REGEXES,
    'reputations': JSON_ALL_REPUTATIONS_INDICATOR_TYPES_REGEXES,
    'readme': [PACKS_INTEGRATION_README_REGEX,
               PACKS_INTEGRATION_NON_SPLIT_README_REGEX,
               PLAYBOOK_README_REGEX,
               PACKS_SCRIPT_README_REGEX,
               PACKS_SCRIPT_NON_SPLIT_README_REGEX
               ],

    'report': [PACKS_REPORT_JSON_REGEX],
    'release-notes': [PACKS_RELEASE_NOTES_REGEX]
}

EXTERNAL_PR_REGEX = r'^pull/(\d+)$'

FILE_TYPES_PATHS_TO_VALIDATE = {
    'reports': JSON_ALL_REPORTS_REGEXES
}

DEF_DOCKER = 'demisto/python:1.3-alpine'
DEF_DOCKER_PWSH = 'demisto/powershell:6.2.3.5563'

DIR_TO_PREFIX = {
    'Integrations': INTEGRATION_PREFIX,
    'Scripts': SCRIPT_PREFIX
}

ENTITY_NAME_SEPARATORS = [' ', '_', '-']

DELETED_YML_FIELDS_BY_DEMISTO = ['fromversion', 'toversion', 'alt_dockerimages', 'script.dockerimage45', 'tests',
                                 'defaultclassifier', 'defaultmapperin', 'defaultmapperout']

DELETED_JSON_FIELDS_BY_DEMISTO = ['fromVersion', 'toVersion']

FILE_EXIST_REASON = 'File already exist'
FILE_NOT_IN_CC_REASON = 'File does not exist in Demisto instance'

ACCEPTED_FILE_EXTENSIONS = [
    '.yml', '.json', '.md', '.py', '.js', '.ps1', '.png', '', '.lock'
]

BANG_COMMAND_NAMES = {'file', 'email', 'domain', 'url', 'ip', 'cve'}

GENERIC_COMMANDS_NAMES = BANG_COMMAND_NAMES.union({'send-mail', 'send-notification', 'cve-latest', 'cve-search'})

DBOT_SCORES_DICT = {
    'DBotScore.Indicator': 'The indicator that was tested.',
    'DBotScore.Type': 'The indicator type.',
    'DBotScore.Vendor': 'The vendor used to calculate the score.',
    'DBotScore.Score': 'The actual score.'
}

IOC_OUTPUTS_DICT = {
    'domain': {'Domain.Name'},
    'file': {'File.MD5', 'File.SHA1', 'File.SHA256'},
    'ip': {'IP.Address'},
    'url': {'URL.Data'}
}
XSOAR_SUPPORT = "xsoar"
XSOAR_AUTHOR = "Cortex XSOAR"
PACK_INITIAL_VERSION = '1.0.0'
PACK_SUPPORT_OPTIONS = ['xsoar', 'partner', 'developer', 'community']

XSOAR_SUPPORT_URL = "https://www.paloaltonetworks.com/cortex"
MARKETPLACE_LIVE_DISCUSSIONS = \
    'https://live.paloaltonetworks.com/t5/cortex-xsoar-discussions/bd-p/Cortex_XSOAR_Discussions'
MARKETPLACE_MIN_VERSION = '6.0.0'

BASE_PACK = "Base"
NON_SUPPORTED_PACK = "NonSupported"
DEPRECATED_CONTENT_PACK = "DeprecatedContent"
IGNORED_DEPENDENCY_CALCULATION = {BASE_PACK, NON_SUPPORTED_PACK, DEPRECATED_CONTENT_PACK}
COMMON_TYPES_PACK = 'CommonTypes'

FEED_REQUIRED_PARAMS = [
    {
        'name': 'feed',
        'must_equal': {
            'defaultvalue': 'true',
            'display': 'Fetch indicators',
            'type': 8,
            'required': False
        },
        'must_contain': {}
    },
    {
        'name': 'feedReputation',
        'must_equal': {
            'display': 'Indicator Reputation',
            'type': 18,
            'required': False,
            'options': ['None', 'Good', 'Suspicious', 'Bad']
        },
        'must_contain': {
            'additionalinfo': 'Indicators from this integration instance will be marked with this reputation'
        }
    },
    {
        'name': 'feedReliability',
        'must_equal': {
            'display': 'Source Reliability',
            'type': 15,
            'required': True,
            'options': [
                'A - Completely reliable', 'B - Usually reliable', 'C - Fairly reliable', 'D - Not usually reliable',
                'E - Unreliable', 'F - Reliability cannot be judged']
        },
        'must_contain': {
            'additionalinfo': 'Reliability of the source providing the intelligence data'
        }
    },
    {
        'name': 'feedExpirationPolicy',
        'must_equal': {
            'display': "",
            'type': 17,
            'required': False,
            'options': ['never', 'interval', 'indicatorType', 'suddenDeath']
        },
        'must_contain': {}
    },
    {
        'name': 'feedExpirationInterval',
        'must_equal': {
            'display': "",
            'type': 1,
            'required': False
        },
        'must_contain': {}
    },
    {
        'name': 'feedFetchInterval',
        'must_equal': {
            'display': 'Feed Fetch Interval',
            'type': 19,
            'required': False
        },
        'must_contain': {}
    },
    {
        'name': 'feedBypassExclusionList',
        'must_equal': {
            'display': 'Bypass exclusion list',
            'type': 8,
            'required': False
        },
        'must_contain': {
            'additionalinfo': 'When selected, the exclusion list is ignored for indicators from this feed.'
                              ' This means that if an indicator from this feed is on the exclusion list,'
                              ' the indicator might still be added to the system.'
        }
    },
    {
        'name': 'feedTags',
        'must_equal': {
            'display': 'Tags',
            'required': False,
            'type': 0
        },
        'must_contain': {
            'additionalinfo': 'Supports CSV values.'
        }
    },
    {
        'name': 'tlp_color',
        'must_equal': {
            'display': 'Traffic Light Protocol Color',
            'options': ['RED', 'AMBER', 'GREEN', 'WHITE'],
            'required': False,
            'type': 15
        },
        'must_contain': {
            'additionalinfo': 'The Traffic Light Protocol (TLP) designation to apply to indicators fetched from the '
                              'feed'
        }
    }
]

FETCH_REQUIRED_PARAMS = [
    {
        'display': 'Incident type',
        'name': 'incidentType',
        'required': False,
        'type': 13
    },
    {
        'display': 'Fetch incidents',
        'name': 'isFetch',
        'required': False,
        'type': 8
    }
]

MAX_FETCH_PARAM = {
    'name': 'max_fetch',
    'required': False,
    'type': 0,
    'defaultvalue': '50'
}

# for reference, the defaultvalue and display are not enforced.
FIRST_FETCH_PARAM = {
    'defaultvalue': '7 days',
    'display': 'First fetch timestamp (<number> <time unit>, e.g., 12 hours, 7 days)',
    'name': 'first_fetch',
    'required': False,
    'type': 0
}

DOCS_COMMAND_SECTION_REGEX = r'(?:###\s{}).+?(?:(?=(?:\n###\s))|(?=(?:\n##\s))|\Z)'
# Ignore list for all 'run_all_validations_on_file' method
ALL_FILES_VALIDATION_IGNORE_WHITELIST = [
    'pack_metadata.json',  # this file is validated under 'validate_pack_unique_files' method
    'testdata',
    'test_data',
    'data_test',
    'testcommandsfunctions',
    'testhelperfunctions',
    'stixdecodetest',
    'testcommands',
    'setgridfield_test',
    'ipnetwork_test',
    'test-data',
    'testplaybook'
]
VALIDATED_PACK_ITEM_TYPES = [
    'Playbooks',
    'Integration',
    'Script',
    'IncidentFields',
    'IncidentTypes',
    'Classifiers',
    'Layouts'
]

FIRST_FETCH = 'first_fetch'

MAX_FETCH = 'max_fetch'

OLDEST_SUPPORTED_VERSION = '5.0.0'

FEATURE_BRANCHES = ['v4.5.0']

SKIP_RELEASE_NOTES_FOR_TYPES = (FileType.RELEASE_NOTES, FileType.README, FileType.TEST_PLAYBOOK,
                                FileType.TEST_SCRIPT, FileType.DOC_IMAGE)

LAYOUT_AND_MAPPER_BUILT_IN_FIELDS = ['indicatortype', 'source', 'comment', 'aggregatedreliability', 'detectedips',
                                     'detectedhosts', 'modified', 'expiration', 'timestamp', 'shortdesc',
                                     'short_description', 'description', 'Tags', 'blocked']

UUID_REGEX = r'[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}'

DEFAULT_ID_SET_PATH = "./Tests/id_set.json"

CONTEXT_OUTPUT_README_TABLE_HEADER = '| **Path** | **Type** | **Description** |'

ARGUMENT_FIELDS_TO_CHECK = ['default', 'required', 'isArray']

PARAM_FIELDS_TO_CHECK = ['type', 'required']


class ContentItems(Enum):
    # the format is defined in issue #19786, may change in the future
    SCRIPTS = 'automation'
    PLAYBOOKS = 'playbook'
    INTEGRATIONS = 'integration'
    INCIDENT_FIELDS = 'incidentfield'
    INCIDENT_TYPES = 'incidenttype'
    DASHBOARDS = 'dashboard'
    INDICATOR_FIELDS = 'indicatorfield'
    REPORTS = 'report'
    INDICATOR_TYPES = 'reputation'
    LAYOUTS = 'layoutscontainer'
    CLASSIFIERS = 'classifier'
    WIDGETS = 'widget'


YML_SUPPORTED_FOLDERS = {
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PLAYBOOKS_DIR,
    TEST_PLAYBOOKS_DIR
}

JSON_SUPPORTED_FOLDERS = {
    CLASSIFIERS_DIR,
    CONNECTIONS_DIR,
    DASHBOARDS_DIR,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR,
    LAYOUTS_DIR,
    INDICATOR_TYPES_DIR,
    REPORTS_DIR,
    WIDGETS_DIR
}

CONTENT_ITEMS_DISPLAY_FOLDERS = {
    SCRIPTS_DIR,
    DASHBOARDS_DIR,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INTEGRATIONS_DIR,
    PLAYBOOKS_DIR,
    INDICATOR_FIELDS_DIR,
    REPORTS_DIR,
    INDICATOR_TYPES_DIR,
    LAYOUTS_DIR,
    CLASSIFIERS_DIR,
    WIDGETS_DIR
}


class DemistoException(Exception):
    pass
