import json
import yaml


class XSOARIntegration:
    def __init__(self, commonfields, name, display, category, image, description, detaileddescription, configuration,
                 script):
        self.commonfields = commonfields
        self.name = name
        self.display = display
        self.category = category
        self.image = image
        self.description = description
        self.detaileddescription = detaileddescription
        self.configuration = configuration
        self.script = script

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    def to_yaml(self):
        return yaml.load(self.to_json())

    @classmethod
    def get_base_integration(cls):
        commonfields = XSOARIntegration.CommonFields('GeneratedIntegration', -1)
        name = 'GeneratedIntegration'
        display = 'GeneratedIntegration'
        category = 'Utilities'
        image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHgAAAAyCAYAAACXpx/YAAAABGdBTUEAALGPC/xh" \
                "BQAACYJJREFUeAHtmwmMVdUdhw8zDDMKjIAgIohIRUaghBSLGmWJWGONaAON2CUmik2pTRu7poCEqq3VtjY2Fl" \
                "vcWqRY1BRJwaWtSSmWxYgooAiOwAAKZREBkZ2Zft+bd8jlOW8YMhSYy/sl39yz3bP8/+eee++5b0IoqGCBlFhg" \
                "JON4GWbBNSkZU2EYWQtcFYqbVYVfXLUwjB+0IDQLG0jveypYp+hUGCRjHBqG9awKX+jeP9xQcUno32kFaVecCm" \
                "M/VRy8MPx7TeusQ6vDko2dCS8qOLjpWqA5XX8YtsAemBq27zkn1ITqsHHn5rCvWgd7LzZ/JUyAVKpZKkcVwujQ" \
                "qsXtYcrwtqFjqw6ZMZYWtcDBtePdX7037Nz3SSZ93fZNYfTMEpw+hvizabNHWpfo/mFEr4/CueVdQoui0gzRuX" \
                "qwhLS2Ze0y9O1YEa69cB2pl6XNuY7HpSyNKsKpR16dDlTvD9v3bgunl1i2JI2GSJODb8JBo+Aj6BCKmtXv4Mm" \
                "L54aHXu2dderFHJ/LhlN1SIuDB/Kee3+4d+iWULm1NDz9VjmvRG3yemrzrk04twf5A6AS2oMPXKlTWhw8jPvo" \
                "qjC0+xDgEcsLsh7NXbua3I2gc1UqnevA0vKQtSwsWl/GM3JN2HPgkzB1ybzgk3I+9Wjn1d0L0jLB8400+9qQN7" \
                "vJZLSipzN4sDofx7bEzcVh7BXvheG9Ls07guHT5oe1O/aTPw909n0wH1Kl4pSMZh/jmBoO1rzE0Q2ObqFfpzNC" \
                "v7O75h3fyD6dQ3npBl6VOoWS4tPC5l1nUfbFvOWbaEaalqiD+GD5IT/UHArlCxSFm/rUvvs+uGBOWLY5LZP9" \
                "sPGm5R582KCIvB/mrNbhDdPsKt+BqxpWuGmVqv9dsWmNJdnbc4jMDWXNd4fWLXZmMrqU7wqPXT+Ie/SBcPP" \
                "0BWHz7paZ9J1725K2g/Bg2J5JS9GfNC3RSbesJ9KbJ+qLwQewPuHD3d/lHl2d+eBQubWC452krwKd+ib4wJU" \
                "6pXWJ1lG7YA68AGew8VHJ7lZxZh96QOe3SfNVyV94vAapdC7jSs17sGOpT2vCog0tg3vPew/s5oGqHYXd7Cgo" \
                "JRbwCXkKfJhlYkrGVRhGjgX8VUftw1VORlqjaXiKdrn9OgyE7lANm2Au/BVWQEOlPZwAtU/eDT2rUO7/ZgF/Cuu" \
                "HArc18rGUvF/CrTAE3N0qgqScHM/DdPgxeKWfC2l9y2BoJ78eo4v5nHqkdD9EeGX/Da6E06EDuHf9O/Dqvwe6Q" \
                "UEnyAIuxUdyZEPy/Y20+i342nQdlMJwmAa+K38PCjrOFvADQ0McaJn6JsOsbL/P5OgHB69cnZ6s23flgo6zBX" \
                "bTXtIJ+cL/oFx/uADcwuwIneEz0B18qHKZ/j3UVafn94GCjrMFfNLN59QjpXv176nnfHfBHoXeUNAJssA22j2S" \
                "I482/wPqHAftT9CYCs0mLOCu1NE6MF9577FfAz8bpkpNeaPjLTyxGJ6EN+Bj8B7bE/zPwc9BJ/AeK2Xge20x+J" \
                "q0AzxvEvhaVFDBAgULFCxQsEDBAgULFCxwTC3gK4EPJrkc00YaUdnVnLsWhh5lHXFcTfWDwU8Z73+g9CjHfVjx" \
                "ImLfAX9umot5J4NOoxN+2fF4NIrj8sm6ITqPQrPhooYUPsZl6mrbp31p1JtOcnaPoLL/Jjru/u2ppO4MdjCUn" \
                "4BB19X2ePohjVLyKl1ITf4bR8SN99fhV6DshO+et4GzahTMB3eUZkFyCfVXiuZPBjckZoPvpL+BDfAMXABRlh8" \
                "LM8D6FkB9+786ws0J32VnQwUcSfdT4HH4JrhaLYUbQfkFyTz1F1iUCdXuW08j7L+kvgv+sCBqIAHt45bnSvCHf" \
                "L5XK9t6BCy/Dn4EA2A6rAfL+oVK++dr2zqsP0p/PAXa0y9cP4FiUFeCdWqX2eCF6vktINwFNXAn3J6lN0c1AQ6" \
                "Cm/VPgJ1100A9DXfDSNDR5kXtI7Af/gATwfrdiNBY92bjD3CMsrztTAXr1HHvgAa4ATxfQ6ieoFGfA9ueB048yy" \
                "YVx9U1m2jdtrEANLhO2QiqFzge23ESagfrs2wl3AwPged/FspAp/8dtM0/QcPHCWNbxleDdvWcb8AUcMfMT5O2d" \
                "RnU1TbJGVv48UPFvmwnPAGeAs8fAyraaBPhcTATzB8Chxy8k7CGlVGgnAHLYSHoBA2alA1fBF7lVtgXlGU1mLK" \
                "MHXMSRK0gYJ1RlnfwUQ8TsD4nWux8dPCDpNlXHdcWvgyWTa4IRA+NK+lgJ4ZjUmPB8yqMoNFg/BIj6HIwfivYz" \
                "pngODzPSRbzCGacZ7zcCNLB1fB5IznqRPxaMP9n2bzctk22jujg2BcnbdQSAjpURRtpC6Ut7M94jR/lTLKD8ng" \
                "2UcNPAmfpKohOIxhugSp4CQaB6l57yPzVmMqBbIYYN20jaLSkLBe1PBvoGBMSxwsJu4qsga3wLKgOtYd6/zpox" \
                "6Tsg2pTe/jUX9tR2sJ2toC2aQ+VsBq8EK4BJ8Hb4MURtZfAazHCsQ+8Ak7uO8Dxng8NUezLq4nChh1zsv/Rxt" \
                "HxbZIOTpx7KNiK0PfBjjprh4Kys0/Ao9AN7oZjqTjzq+qo9H3SdsHZUJIguUKQfNSKE6x59sx12aPOS7bzQ+K" \
                "WnQXa5x54F4ZBfXqGTOvuDFdDnGgEM/V5jG0bTir2RbtHGXZCuarkVbLCEZTyvhE1g8AEaA194QV4BLyflILy" \
                "fBtyiWmsXIa+COfB9eAM9SrRIKpH7SH8meNtMBHugxrQ2c9DY/RB9uSvcPSKnQurYBxsA5fEwfBH0OHfgjHwJH" \
                "jlJK9eop9SGSnet7vAdWA8Krftd2JG9hj78m3iVVABXgSTwPHXq7vItVAuzsj9MBZUPzgAvzaCXBp96PgYfg6e" \
                "/yVQzs7JmVDtn/c4/CsRn0N4ZSJu+cXg0mI9SyEuS06mZWDb0Si3ENYJljXdiZerOK6u2YypHOM9zaRR4PmXG" \
                "kEl8AqY5hXaDpzMr4Np8ibECfdiIt28NXAHqNy2THMl2AbWre3eAMuputrOrcOLzElmW9rdid4KVLwHO3FUOVj" \
                "uASONkfcjO9dY6eA/gStCNCDBQ2pGyHSPUYZ1XnR6TG/ssQsVOK6kOhBJpvUmvhNcavvB5fAyONnrs4d9bQP5" \
                "VFfbuWU7kRAdm5t30sZzr/iTtqPZjn2Vo1fRjeDD4gBYDo19DqCKdGomw/pBExqatw3vf3HJ3ZCNn3WyjeF/Pm" \
                "PRmBKd/dAAAAAASUVORK5CYII="
        description = 'Generated integration'
        detaileddescription = 'This integration was auto generated by the Cortex XSOAR SDK.'

        configurations = [XSOARIntegration.Configuration(display='Server URL (e.g. https://soar.monstersofhack.com)',
                                                         name='url',
                                                         defaultvalue='https://soar.monstersofhack.com',
                                                         type_=0,
                                                         required=True),
                          XSOARIntegration.Configuration(display='Fetch incidents',
                                                         name='isFetch',
                                                         type_=8,
                                                         required=False),
                          XSOARIntegration.Configuration(display='Incident type',
                                                         name='incidentType',
                                                         type_=13,
                                                         required=False),
                          XSOARIntegration.Configuration(display='Maximum number of incidents per fetch',
                                                         name='max_fetch',
                                                         defaultvalue='10',
                                                         type_=0,
                                                         required=False),
                          XSOARIntegration.Configuration(display='API Key',
                                                         name='apikey',
                                                         type_=4,
                                                         required=True),
                          XSOARIntegration.Configuration(display='Score threshold for ip reputation command (0-100)',
                                                         name='threshold_ip',
                                                         defaultvalue='65',
                                                         type_=0,
                                                         required=False),
                          XSOARIntegration.Configuration(display='Score threshold for domain reputation command (0-100)',
                                                         name='threshold_domain',
                                                         defaultvalue='65',
                                                         type_=0,
                                                         required=False),
                          XSOARIntegration.Configuration(display='Fetch alerts with status (ACTIVE, CLOSED)',
                                                         name='alert_status',
                                                         defaultvalue='ACTIVE',
                                                         type_=15,
                                                         required=False,
                                                         options=['ACTIVE', 'CLOSED']),
                          XSOARIntegration.Configuration(display='Fetch alerts with type',
                                                         name='alert_type',
                                                         type_=0,
                                                         required=False),
                          XSOARIntegration.Configuration(display='Minimum severity of alerts to fetch',
                                                         name='min_severity',
                                                         defaultvalue='Low',
                                                         type_=15,
                                                         required=True,
                                                         options=['Low', 'Medium', 'High', 'Critical']),
                          XSOARIntegration.Configuration(display='Trust any certificate (not secure)',
                                                         name='insecure',
                                                         type_=8,
                                                         required=False),
                          XSOARIntegration.Configuration(display='Use system proxy settings',
                                                         name='proxy',
                                                         type_=8,
                                                         required=False)]

        script = XSOARIntegration.Script('', 'python', 'python3', 'demisto/python3:3.8.3.9324', True, False)

        return cls(commonfields, name, display, category, image, description, detaileddescription, configurations,
                   script)

    class CommonFields:
        def __init__(self, id_, version):
            self.id = id_
            self.version = version

    class Configuration:
        def __init__(self, name, display, type_, required, defaultvalue='', options=None):
            self.name = name
            self.display = display
            self.defaultvalue = defaultvalue
            self.type = type_
            self.required = required
            if options:
                self.options = options
            if defaultvalue:
                self.defaultvalue = defaultvalue

    class Script:
        def __init__(self, script, type_, subtype, dockerimage, isfetch, runonce, commands=None):
            self.script = script
            self.type = type_
            self.subtype = subtype
            self.dockerimage = dockerimage
            self.isfetch = isfetch
            self.runonce = runonce
            if commands:
                self.commands = commands

        class Command:
            def __init__(self, name, description, arguments=None, outputs=None):
                self.name = name
                self.description = description
                if arguments:
                    self.arguments = arguments
                if outputs:
                    self.outputs = outputs

            class Argument:
                def __init__(self, name, description, required, auto=None, predefined=None):
                    self.name = name
                    self.description = description
                    self.required = required
                    if auto:
                        self.auto = auto
                    if predefined:
                        self.predefined = predefined

            class Output:
                def __init__(self, type_, context_path, description):
                    self.type = type_
                    self.contextPath = context_path
                    self.description = description
