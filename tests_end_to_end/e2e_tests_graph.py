from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack


def test_graph_e2e():
    with ContentGraphInterface() as graph:
        hello_world = graph.search(object_id="HelloWorld")
        hello_world_packs = [x for x in hello_world if isinstance(x, Pack)]
        hello_world_integrations = [
            x for x in hello_world if isinstance(x, Integration)
        ]
        hello_world_classifiers = [x for x in hello_world if isinstance(x, Classifier)]
        assert hello_world
        assert hello_world_packs, "HelloWorld pack not found in graph"
        assert hello_world_integrations, "HelloWorld integration not found in graph"
        assert hello_world_classifiers, "HelloWorld classifier not found in graph"
        hello_world_pack = hello_world_packs[0]
        hello_world_integration = hello_world_integrations[0]
        hello_world_classifier = hello_world_classifiers[0]
        assert hello_world_integration.in_pack
        assert hello_world_integration.in_pack.object_id == hello_world_pack.object_id
        classifier_uses_items = hello_world_classifier.uses
        assert classifier_uses_items
        assert classifier_uses_items[0].content_item_to.object_id == "Hello World Alert"

        aws_s3 = graph.search(
            object_id="AWS - S3", content_type=ContentType.INTEGRATION
        )
        assert aws_s3, "AWS-S3 integration not found in graph"
        aws_s3_integration = aws_s3[0]
        assert isinstance(aws_s3_integration, Integration)
        assert aws_s3_integration.tested_by[0].object_id == "AWS - S3 Test Playbook"
        assert aws_s3_integration.imports[0].object_id == "AWSApiModule"


if __name__ == "__main__":
    test_graph_e2e()
