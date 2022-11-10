import pytest


@pytest.fixture
def demisto_tenants_request(requests_mock, demisto_soft_404_error_page):
    """Registers a mock response for the `/accounts` endpoint of a demisto server.
    Single instance deployment and tenant hosts will redirect to a soft 404 error page.

    Args:
        host (str): The hostname of the demisto server. Should match the `DEMISTO_BASE_URL` envvar.
        names (list, optional): A list of tenant names to create for the mock response. Defaults to ["tenant1"].
    """
    def factory(
        host,
        names=["tenant1"]
    ):
        # Create mock tenants
        tenants = [
            {
                "adminUsers": [
                    "admin"
                ],
                "cacheVersn": 0,
                "created": "2019-04-19T17:38:01.454264286Z",
                "createdOnMaster": False,
                "displayName": name,
                "elasticIsUsed": False,
                "guid": "92015eea-94a5-4483-b7e3-bb9ec06e538d",
                "hostGroupId": "10",
                "hostStates": {
                    "16": "ready"
                },
                "id": "206",
                "modified": "2022-10-03T19:43:26.092870278Z",
                "name": f"acc_{name}",
                "notActive": False,
                "portId": 206,
                "propagationLabels": [
                    name
                ],
                "roles": {
                    "roles": [
                        "Administrator"
                    ],
                    "valid": True
                },
                "server": None,
                "status": "ready",
                "useDynamicPort": False,
                "version": 1009
            }
            for name in names
        ]
        # Register error page and redirect if the host doesn't have tenants or is itself a tenant
        if not tenants or "acc_" in host:
            demisto_soft_404_error_page(host)
            return requests_mock.get(
                f"https://{host}/accounts",
                status_code=301,
                headers={"location": f"https://{host}/#/404"}
            )
        else:
            return requests_mock.get(
                f"https://{host}/accounts",
                json=tenants
            )

    return factory


@pytest.fixture
def demisto_soft_404_error_page(requests_mock):
    """Registers a mock response for a soft 404 error page.
    This response will have a 200 status code, but the page contents indicate that the request was invalid.

    Args:
        host (str): The hostname of the demisto server. Should match the `DEMISTO_BASE_URL` envvar.
    """
    def factory(host):
        return requests_mock.get(
            f"https://{host}/#/404",
            text='''<!doctype html>
            <html lang="en">
            <head>
                <title>Cortex XSOAR</title>
                <meta charset="utf-8">
                <meta name="description" content="Cortex XSOAR">
                <meta name="keywords" content="security,incident response,attack playback,forensics">
                <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
                <link rel="shortcut icon" href="/favicon.ico?v=1653837745748">
                <link href="/assets/light-bundle-1653837745748.css?v=1653837745748" rel="stylesheet">
            </head>
            <body>
                <div id="app"></div>
                <script src="/assets/light-bundle-1653837745748.js?v=1653837745748"></script>
            </body>
            </html>
            '''
        )
    return factory
