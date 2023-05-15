import sys

import networkx as nx


def compare_graphml_files(file1, file2):
    # Read GraphML files
    graph1 = nx.graphml.read_graphml(file1)
    graph2 = nx.graphml.read_graphml(file2)

    # Compare nodes
    nodes1 = set(graph1.nodes())
    nodes2 = set(graph2.nodes())
    added_nodes = nodes2 - nodes1
    removed_nodes = nodes1 - nodes2

    # Compare edges
    edges1 = set(graph1.edges())
    edges2 = set(graph2.edges())
    added_edges = edges2 - edges1
    removed_edges = edges1 - edges2

    # Print comparison results
    print("Nodes added: ", added_nodes)  # noqa
    print("Nodes removed: ", removed_nodes)  # noqa
    print("Edges added: ", added_edges)  # noqa
    print("Edges removed: ", removed_edges)  # noqa


if __name__ == "__main__":
    compare_graphml_files(sys.argv[1], sys.argv[2])
