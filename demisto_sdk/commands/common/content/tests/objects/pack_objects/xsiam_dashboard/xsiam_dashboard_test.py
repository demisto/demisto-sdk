from demisto_sdk.commands.common.content.objects.pack_objects import XSIAMDashboard
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object


def get_xsiam_dashboard(pack, name):
    return pack.create_xsiam_dashboard(
        name,
        {
            "dashboards_data": [
                {"global_id": "xsiam_dashboard_id", "name": "xsiam_dashboard_name"}
            ]
        },
    )


def test_objects_factory(pack):
    xsiam_dashboard = get_xsiam_dashboard(pack, "xsiam_dashboard_name")
    obj = path_to_pack_object(xsiam_dashboard.xsiam_dashboard_tmp_path)
    assert isinstance(obj, XSIAMDashboard)


def test_prefix(pack):
    xsiam_dashboard = get_xsiam_dashboard(
        pack, "external-xsiamdashboard-xsiam_dashboard_name"
    )

    obj = XSIAMDashboard(xsiam_dashboard.xsiam_dashboard_tmp_path)
    assert obj.normalize_file_name() == xsiam_dashboard.xsiam_dashboard_tmp_path.name

    xsiam_dashboard = get_xsiam_dashboard(pack, "xsiam_dashboard_name")

    obj = XSIAMDashboard(xsiam_dashboard.xsiam_dashboard_tmp_path)
    assert (
        obj.normalize_file_name()
        == f"external-xsiamdashboard-{xsiam_dashboard.xsiam_dashboard_tmp_path.name}"
    )
