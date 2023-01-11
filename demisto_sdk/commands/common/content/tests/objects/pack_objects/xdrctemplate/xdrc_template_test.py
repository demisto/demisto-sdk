from demisto_sdk.commands.common.content.objects.pack_objects import XDRCTemplate
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object


class TestXDRCTemplate:
    def test_objects_factory(self, pack):
        xdrc_template = pack.create_xdrc_template("xdrc_template_name")
        obj = path_to_pack_object(xdrc_template.xdrc_template_tmp_path)
        assert isinstance(obj, XDRCTemplate)

    def test_prefix(self, pack):
        xdrc_template = pack.create_xdrc_template(
            "external-xdrctemplate-xdrc_template_name"
        )
        obj = XDRCTemplate(xdrc_template.xdrc_template_tmp_path)
        assert obj.normalize_file_name() == xdrc_template.xdrc_template_tmp_path.name

        xdrc_template = pack.create_xdrc_template("xdrc_template_name")
        obj = XDRCTemplate(xdrc_template.xdrc_template_tmp_path)
        assert (
            obj.normalize_file_name()
            == f"external-xdrctemplate-{xdrc_template.xdrc_template_tmp_path.name}"
        )

    def test_files_detection(self, pack):
        xdrc_template = pack.create_xdrc_template("xdrc_template_name")
        obj = XDRCTemplate(xdrc_template.xdrc_template_tmp_path)
        assert obj.path == xdrc_template.xdrc_template_tmp_path
