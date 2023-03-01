from demisto_sdk.commands.common.content.objects.pack_objects import XSIAMReport
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object


def get_xsiam_report(pack, name):
    return pack.create_xsiam_report(
        name,
        {
            "templates_data": [
                {"global_id": "xsiam_report_id", "name": "xsiam_report_name"}
            ]
        },
    )


def test_objects_factory(pack):
    xsiam_report = get_xsiam_report(pack, "xsiam_report_name")
    obj = path_to_pack_object(xsiam_report.xsiam_report_tmp_path)
    assert isinstance(obj, XSIAMReport)


def test_prefix(pack):
    xsiam_report = get_xsiam_report(pack, "external-xsiamreport-xsiam_report_name")

    obj = XSIAMReport(xsiam_report.xsiam_report_tmp_path)
    assert obj.normalize_file_name() == xsiam_report.xsiam_report_tmp_path.name

    xsiam_report = get_xsiam_report(pack, "xsiam_report_name")

    obj = XSIAMReport(xsiam_report.xsiam_report_tmp_path)
    assert (
        obj.normalize_file_name()
        == f"external-xsiamreport-{xsiam_report.xsiam_report_tmp_path.name}"
    )
