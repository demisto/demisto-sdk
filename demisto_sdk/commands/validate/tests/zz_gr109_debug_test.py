from demisto_sdk.commands.validate.tests.GR_validators_test import *  # noqa


def test_debug(repo_for_test_gr_109_unknown_dependency):
    gi = repo_for_test_gr_109_unknown_dependency.create_graph()
    res = gi.search(content_type=ContentType.PLAYBOOK, object_id="playbook1")
    print("SEARCH_RESULT", [(type(r).__name__, r.object_id) for r in res])
    for obj in gi._id_to_obj.values():
        if getattr(obj, "object_id", None) == "playbook1":
            print("PB", type(obj).__name__, id(obj))
            for rel in obj.uses:
                t = rel.content_item_to
                print("  USES", type(t).__name__, t.object_id, rel.mandatorily, getattr(t, "not_in_repository", None))
    from demisto_sdk.commands.content_graph.interface.neo4j.queries.validations import validate_unknown_content
    with gi.driver.session() as s:
        r = s.execute_read(validate_unknown_content, [])
    print("UNKNOWN_QUERY", {k: [n.get("object_id") for n in v.nodes_to] for k, v in r.items()})
