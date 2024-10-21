# Demisto-SDK docker

Run Demisto-SDK validations from within a docker container.

You can use this image to run Demisto-SDK commands locally or as a CI/CD process.

## Get The Docker Image

Pull the docker image with:
`docker pull demisto/demisto-sdk:<tag>`

You can find the latest tags in the docker hub:
`http://hub.docker.com/r/demisto/demisto-sdk`

## The Content Repository

To use the Demisto-SDK, ensure you have a content-like repository with Cortex XSOAR content in a structure that matches the official [XSOAR Content repo](https://github.com/demisto/content).

You can generate such a repository using the following [template](https://github.com/demisto/content-external-template)

## Mounts

Demisto-SDK uses volume mounts to run on the local content repository.
_Please note that mounting on macOS and Windows may cause slowness._

To ensure the best performance, please either:

- Use a Linux machine
- Use [Windows WSL2](https://docs.microsoft.com/en-us/windows/wsl/install)

## Environment Variable

Some commands such as `demisto-sdk upload` and `demisto-sdk run` need the following environment variables to communicate with your XSOAR Server:

- `DEMISTO_BASE_URL`  
    The URL of the XSOAR server to communicate with
- `DEMISTO_API_KEY`  
    API Key (Can be generated from XSOAR -> Settings -> API Key)
- `DEMISTO_VERIFY_SSL` (Default: true)  
    Whether to verify SSL certificates.

To pass those variables, you should add the following option:

```sh
docker run --env DEMISTO_BASE_URL="https://xsoar.com:443" <rest of the command>
```

You can also use an env file:

.env

```sh
DEMISTO_BASE_URL="https://xsoar.com:443"
DEMISTO_API_KEY="xxxxxxxxxxxxx"
```

Command:

```sh
docker run --env-file .env <rest of the command>
```

## Docker In Docker (Docker Daemon Binding)

To achieve Docker In Docker behavior. We want to bind the Docker Daemon with the following option:

- `--mount source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind`  
    Mounts the docker daemon container to use docker commands from within a docker container.

## Examples

(All examples use Cortex XSOAR's official [content repository](https://github.com/demisto/content)).

## Alias for easy usage

You can create an alias to the command by adding the following line to your shell configuration files:

```sh
alias demisto-sdk="docker run -it --rm \
--mount type=bind,source="$(pwd)",target=/content \
--mount source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind \
demisto/demisto-sdk:<tag>"
```

### Validate command

For more information about the validate command, please refer to its [documentation.](https://github.com/demisto/demisto-sdk/blob/master/demisto_sdk/commands/validate/README.md) on the [demisto-sdk repo](https://github.com/demisto/demisto-sdk).

```sh
docker run -it --rm \
--mount type=bind,source="$(pwd)",target=/content \
--mount source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind \
demisto/demisto-sdk:<tag> \
demisto-sdk validate -i Packs/ipinfo/Integrations/ipinfo_v2
```

#### Breaking down command arguments

- `docker run`  
    Creates a container (if one does not exist) and runs the following command inside it
- `-it`  
    Keep the stdin open and connects tty
- `--rm`  
    Removes the docker container when done (ommit this part to re-use the container in the future)
- `--mount type=bind,source="$(pwd)",target=/content`  
    Connects the pwd (assuming you're in content) to the container's content directory
- `--mount source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind`  
Bind the docker daemon to the container to enable execute docker-from-docker.
- `demisto/demisto-sdk:\<tag>` (Replace the tag with locked version, can be found at the [Docker Hub](https://hub.docker.com/r/demisto/demisto-sdk))  
    The docker image name  
- `demisto-sdk validate -i Packs/ipinfo/Integrations/ipinfo_v2`
    The demisto-sdk command to be run inside the container
