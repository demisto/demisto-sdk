from demisto_sdk.commands.common.content.objects.pack_objects import Trigger
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object


def get_trigger(pack, name):
    return pack.create_trigger(
        name, {"trigger_id": "trigger_id", "trigger_name": "trigger_name"}
    )


def test_objects_factory(pack):
    trigger = get_trigger(pack, "trigger_name")
    obj = path_to_pack_object(trigger.trigger_tmp_path)
    assert isinstance(obj, Trigger)


def test_prefix(pack):
    trigger = get_trigger(pack, "external-trigger-trigger_name")

    obj = Trigger(trigger.trigger_tmp_path)
    assert obj.normalize_file_name() == trigger.trigger_tmp_path.name

    trigger = get_trigger(pack, "trigger_name")

    obj = Trigger(trigger.trigger_tmp_path)
    assert (
        obj.normalize_file_name() == f"external-trigger-{trigger.trigger_tmp_path.name}"
    )
