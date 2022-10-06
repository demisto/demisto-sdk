## Content Graph Commands

**A set of commands used for creating, loading and managing a graph database representation of content repository.**

### Architecture
The database is implemented with [neo4j](https://neo4j.com/) platform, and populated with data using [neo4j python driver](https://neo4j.com/docs/api/python-driver/current/api.html).
In the database, every content object has a unique **node** which contains its properties. Nodes of content objects that are associated with each other (E.g., a playbook A uses a script B) have a directed **relationship** between them.

![Architecture](images/architecture.png)

#### Relationship Types
* IN_PACK
* USES
* HAS_COMMAND
* TESTED_BY
* IMPORTS
* DEPENDS_ON

### create-content-graph
**Creates a content graph from a given repository.**
This commands parses all content packs under the repository, including their relationships. Then, the parsed content objects are mapped to a Repository model and uploaded to the database.

![Parsers](images/parsers.png) ![Models](images/models.png)

#### Arguments
* **-nd, --no-use-docker**

    Do not use docker to create the content graph.

* **-us, --use-existing**

    Use existing service.

* **-v, --verbose**

    Verbosity level -v / -vv / .. / -vvv.

* **-q, --quite**

    Quiet output, only output results in the end.

* **-lp, --log-path**

    Path to store all levels of logs.


### load-content-graph
**Loads a content graph from a given dump file.**

#### Arguments
* **-nd, --no-use-docker**

    Do not use docker to create the content graph.

* **-cgp, --content-graph-path**

    Path to the content graph dump file.

* **-us, --use-existing**

    Use existing service.

* **-v, --verbose**

    Verbosity level -v / -vv / .. / -vvv.

* **-q, --quite**

    Quiet output, only output results in the end.

* **-lp, --log-path**

    Path to store all levels of logs.
