import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional

import dateparser
import google.auth
import requests
from google.auth.transport.requests import Request
from packaging.version import InvalidVersion, Version
from requests.exceptions import ConnectionError, RequestException, Timeout

from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.common.tools import retry

DOCKERHUB_USER = "DOCKERHUB_USER"
DOCKERHUB_PASSWORD = "DOCKERHUB_PASSWORD"
DEFAULT_REPOSITORY = "demisto"
IS_CONTENT_GITLAB_CI = os.getenv("CONTENT_GITLAB_CI")
DOCKER_IO = os.getenv("DOCKER_IO", "")


class DockerHubAuthScope(StrEnum):
    PULL = "pull"  # Grants read-only access to the repository, allowing you to pull images.
    PUSH = "push"  # Grants write access to the repository, allowing you to push images.
    DELETE = "delete"  # Grants permission to delete images from the repository.
    REPOSITORY = "repository"  # Grants full access to the repository, including both pull and push permissions.


class DockerHubRequestException(Exception):
    def __init__(self, message: str, exception: RequestException):
        super().__init__(message)
        self.message = message
        self.exception = exception

    def __str__(self):
        return f"Error - {self.message} - Exception - {self.exception}"


@lru_cache
class DockerHubClient:
    DEFAULT_REGISTRY = "https://registry-1.docker.io/v2"
    DOCKER_HUB_API_BASE_URL = "https://hub.docker.com/v2"
    TOKEN_URL = "https://auth.docker.io/token"

    def __init__(
        self,
        docker_hub_api_url: str = "",
        registry: str = "",
        username: str = "",
        password: str = "",
        verify_ssl: bool = False,
    ):
        self.registry_api_url = get_registry_api_url(registry, self.DEFAULT_REGISTRY)
        self.docker_hub_api_url = docker_hub_api_url or self.DOCKER_HUB_API_BASE_URL
        self.username = username or os.getenv(DOCKERHUB_USER, "")
        self.password = password or os.getenv(DOCKERHUB_PASSWORD, "")
        self.auth = (
            (self.username, self.password) if self.username and self.password else None
        )
        self._session = requests.Session()
        self._docker_hub_auth_tokens: Dict[str, Any] = {}
        self.verify_ssl = verify_ssl

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.close()

    @retry(times=5, exceptions=(ConnectionError, Timeout))
    def get_token(
        self, repo: str, scope: DockerHubAuthScope = DockerHubAuthScope.PULL
    ) -> str:
        """
        Retrieves the token for repo's authentication.

        Args:
            repo: the repository to retrieve the token for.
            scope: the scope needed for the repository
        """
        if IS_CONTENT_GITLAB_CI:
            # If running in a Gitlab CI environment, try using the Google Cloud access token
            logger.debug(
                "Attempting to use Google Cloud access token for Docker Hub proxy authentication"
            )
            try:
                if gcloud_access_token := get_gcloud_access_token():
                    logger.debug("returning gcloud_access_token")
                    return gcloud_access_token
            except Exception as e:
                logger.error(f"Failed to get gcloud access token: {e}")

        if token_metadata := self._docker_hub_auth_tokens.get(f"{repo}:{scope}"):
            now = datetime.now()
            if expiration_time := dateparser.parse(token_metadata.get("issued_at")):
                # minus 60 seconds to be on the safe side
                _expiration_time: datetime = expiration_time + timedelta(
                    seconds=token_metadata.get("expires_in_seconds") - 60
                )
                if _expiration_time.replace(tzinfo=None) < now:
                    return token_metadata.get("token")

        params = {
            "service": "registry.docker.io",
            "scope": f"repository:{repo}:{scope}",
        }

        response = self._session.get(
            self.TOKEN_URL,
            params=params,
            auth=self.auth,
        )
        try:
            response.raise_for_status()
        except RequestException as _error:
            logger.debug(f"Error when trying to get dockerhub token, error\n:{_error}")
            if (
                _error.response is not None
                and (
                    _error.response.status_code
                    in (requests.codes.unauthorized, requests.codes.too_many_requests)
                )
                and self.auth
            ):
                # in case of rate-limits with a username:password, retrieve the token without username:password
                logger.debug("Trying to get dockerhub token without username:password")
                try:
                    response = self._session.get(
                        self.TOKEN_URL,
                        params=params,
                    )
                    response.raise_for_status()
                except RequestException as error:
                    raise DockerHubRequestException(
                        f"Failed to get dockerhub token without username:password:\n{error}",
                        exception=error,
                    )
            else:
                raise DockerHubRequestException(
                    "Failed to get dockerhub token with username:password",
                    exception=_error,
                )
        try:
            raw_json_response = response.json()
        except JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to get docker hub token: {response.text}"
            ) from e

        token = raw_json_response.get("token")
        self._docker_hub_auth_tokens[f"{repo}:{scope}"] = {
            "token": token,
            "issued_at": raw_json_response.get("issued_at"),
            "expires_in_seconds": raw_json_response.get("expires_in"),
        }

        return token

    @retry(times=5, exceptions=(ConnectionError, Timeout))
    def get_request(
        self,
        url: str,
        headers: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        """
        Do a get request to a dockerhub endpoint service

        Args:
            url: full URL
            headers: headers if needed
            params: params if needed
        """
        auth = None if headers and "Authorization" in headers else self.auth

        response = self._session.get(
            url,
            headers=headers,
            params=params,
            verify=self.verify_ssl,
            auth=auth,
        )
        response.raise_for_status()
        try:
            return response.json()
        except JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to get response of {url=}, {response.text=}"
            ) from e

    @lru_cache
    def do_docker_hub_get_request(
        self,
        url_suffix: Optional[str] = None,
        next_page_url: Optional[str] = None,
        headers: Optional[frozenset] = None,
        params: Optional[frozenset] = None,
        results_key: str = "results",
    ):
        """
        Do a get request to dockerhub api

        Args:
            url_suffix: the URL suffix
            next_page_url: the URL for the next page if pagination is required
            headers: any custom headers
            params: query parameters
            results_key: the key to retrieve the results in case its a list
        """
        logger.debug("dockerhub_client | do_docker_hub_get_request")
        if url_suffix:
            if not url_suffix.startswith("/"):
                url_suffix = f"/{url_suffix}"
            url = f"{self.docker_hub_api_url}{url_suffix}"
        elif next_page_url:
            url = next_page_url
        else:
            raise ValueError("either url_suffix/next_page_url must be provided")

        _params = params or {"page_size": 1000} if not next_page_url else params

        raw_json_response = self.get_request(
            url,
            headers=(
                {key: value for key, value in headers}
                if headers
                else {"Accept": "application/json"}
            ),
            params=_params,
        )

        amount_of_objects = raw_json_response.get("count")
        if not amount_of_objects:
            # received only a single record
            return raw_json_response

        logger.debug(f"Received {raw_json_response.get('count')} objects from {url=}")
        results = raw_json_response.get(results_key) or []
        # do pagination if needed
        if next_page_url := raw_json_response.get("next"):
            results.extend(
                self.do_docker_hub_get_request(
                    next_page_url=next_page_url,
                    headers=headers,
                    params=params,
                    results_key=results_key,
                )
            )

        return results

    @lru_cache
    def do_registry_get_request(
        self,
        url_suffix: str,
        docker_image: str,
        scope: DockerHubAuthScope = DockerHubAuthScope.PULL,
        headers: Optional[frozenset] = None,
        params: Optional[frozenset] = None,
    ) -> Dict[str, Any]:
        """
        Do a get request to a dockerhub registry

        Args:
            url_suffix: the URL suffix
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            scope: what is the scope for the api-request.
            headers: any custom headers
            params: query parameters
        """
        logger.debug("dockerhub_client | do_registry_get_request")
        if not url_suffix.startswith("/"):
            url_suffix = f"/{url_suffix}"

        return self.get_request(
            f"{self.registry_api_url}/{docker_image}{url_suffix}",
            headers=(
                {key: value for key, value in headers}
                if headers
                else None
                or {
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json,"
                    "application/vnd.docker.distribution.manifest.list.v2+json",
                    "Authorization": f"Bearer {self.get_token(docker_image, scope=scope)}",
                }
            ),
            params={key: value for key, value in params} if params else None,
        )

    def get_image_manifests(self, docker_image: str, tag: str) -> Dict[str, Any]:
        """
        Returns the docker image's manifests

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            tag: The tag of the docker image
        """
        try:
            return self.do_registry_get_request(
                f"/manifests/{tag}", docker_image=docker_image
            )
        except RequestException as error:
            raise DockerHubRequestException(
                f"Failed to image manifests of docker-image {docker_image}:{tag}",
                exception=error,
            )

    def get_image_digest(self, docker_image: str, tag: str) -> str:
        """
        Returns docker image's tag digest.

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            tag: The tag of the docker image
        """
        response = self.get_image_manifests(docker_image, tag=tag)
        try:
            return response["config"]["digest"]
        except KeyError as error:
            raise RuntimeError(
                f"Failed to get docker image {docker_image}'s tag {tag} digest from {response=}"
            ) from error

    def get_image_blobs(self, docker_image: str, image_digest: str) -> Dict[str, Any]:
        """
        Returns the blobs of an image digest

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            image_digest: The docker image's digest
        """
        try:
            return self.do_registry_get_request(
                f"/blobs/{image_digest}", docker_image=docker_image
            )
        except RequestException as error:
            raise DockerHubRequestException(
                f"Failed to retrieve image blobs of docker-image {docker_image} with digest {image_digest}",
                exception=error,
            )

    def get_image_env(self, docker_image: str, tag: str) -> List[str]:
        """
        Get docker image's tag environment metadata.

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            tag: The tag of the docker image
        """
        image_digest = self.get_image_digest(docker_image, tag=tag)
        response = self.get_image_blobs(docker_image, image_digest=image_digest)
        try:
            return response["config"]["Env"]
        except KeyError as e:
            raise RuntimeError(
                f"Failed to get docker image {docker_image}'s tag {tag} env from {response=}"
            ) from e

    def get_image_tags(self, docker_image: str) -> List[str]:
        """
        Lists all the tags of a docker-image.

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
        """
        try:
            response = self.do_registry_get_request(
                "/tags/list", docker_image=docker_image
            )
        except RequestException as error:
            raise DockerHubRequestException(
                f"Failed to retrieve image tags of docker-image {docker_image}",
                exception=error,
            )

        return response.get("tags") or []

    def get_image_tag_metadata(self, docker_image: str, tag: str) -> Dict[str, Any]:
        """
        Returns the docker image's tag metadata

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            tag: The tag of the docker image
        """
        try:
            if IS_CONTENT_GITLAB_CI:
                image_digest = self.get_image_digest(docker_image, tag=tag)
                response = self.get_image_blobs(docker_image, image_digest=image_digest)
                return response
            return self.do_docker_hub_get_request(
                f"/repositories/{docker_image}/tags/{tag}"
            )
        except RequestException as error:
            raise DockerHubRequestException(
                f"Failed to retrieve tag metadata of docker-image {docker_image}:{tag}",
                exception=error,
            )

    def is_docker_image_exist(self, docker_image: str, tag: str) -> bool:
        """
        Returns whether a docker image exists.

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            tag: The tag of the docker image
        """
        try:
            self.get_image_tag_metadata(docker_image, tag=tag)
            return True
        except DockerHubRequestException as error:
            if (
                error.exception.response
                and error.exception.response.status_code == requests.codes.not_found
            ):
                logger.debug(
                    f"docker-image {docker_image}:{tag} does not exist in dockerhub"
                )
                return False
            logger.debug(
                f"Error when trying to fetch {docker_image}:{tag} metadata: {error}"
            )
            return tag in self.get_image_tags(docker_image)

    def get_docker_image_tag_creation_date(
        self, docker_image: str, tag: str
    ) -> datetime:
        """
        Returns the creation date of the docker-image's tag.

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
            tag: The tag of the docker image
        """
        response = self.get_image_tag_metadata(docker_image, tag=tag)
        if creation_date := response.get("created"):
            return datetime.strptime(
                iso8601_to_datetime_str(creation_date), "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        else:
            return datetime.strptime(
                response.get("last_updated", ""), "%Y-%m-%dT%H:%M:%S.%fZ"
            )

    def get_latest_docker_image_tag(self, docker_image: str) -> Version:
        """
        Returns the latest tag of a docker image.

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python
        """
        raw_image_tags = self.get_image_tags(docker_image)
        if not raw_image_tags:
            raise RuntimeError(
                f"The docker image {docker_image} does not have any tags"
            )

        max_version_tag = Version("0.0.0")
        for tag in raw_image_tags:
            try:
                version_tag = Version(tag)
                # the version_tag.release returns a tuple from the version numbers '1.2.3.45' -> (1, 2, 3, 45)
                # The last place is always a build number, therefore always increasing.
                if max_version_tag.release[-1] < version_tag.release[-1]:
                    max_version_tag = version_tag
            except InvalidVersion:
                logger.debug(
                    f"The tag {tag} has invalid version for docker-image {docker_image}, skipping it"
                )

        # Return the version corresponding to the maximum build tag.
        return max_version_tag

    def get_latest_docker_image(self, docker_image: str) -> str:
        """
        Returns the latest docker-image including the tag.

        Args:
            docker_image: The docker-image name, e.g: demisto/pan-os-python

        Returns:
            str: the full docker-image included the tag, for example demisto/pan-os-python:2.0.0

        """
        return f"{docker_image}:{self.get_latest_docker_image_tag(docker_image)}"

    def get_repository_images(
        self, repo: str = DEFAULT_REPOSITORY
    ) -> List[Dict[str, Any]]:
        """
        Returns all the images metadata of a repo.

        Args:
            repo: The repository name, e.g.: demisto
        """
        try:
            return self.do_docker_hub_get_request(f"/repositories/{repo}")
        except RequestException as error:
            raise DockerHubRequestException(
                f"Failed to retrieve images of repository {repo}", exception=error
            )

    def get_repository_images_names(self, repo: str = DEFAULT_REPOSITORY) -> List[str]:
        """
        Returns a list of the images within a repository

        Args:
            repo: The repository name, e.g.: demisto
        """
        return [
            image_metadata.get("name", "")
            for image_metadata in self.get_repository_images(repo)
            if image_metadata.get("name")
        ]


### Google Artifactory functions ###


def get_dockerhub_artifact_registry_url(base_path: str) -> str:
    """
    Parses a DockerHub Google Artifact Registry internal base path into a base url for DockerHub proxy API calls.
    See Confluence page: Shared-Services GCP Services - GAR.

    Args:
    base_path (str): The base path of the Google Artifact Registry in the format 'region-domain/project/repository'.

    Returns:
        str: The base URL for the DockerHub proxy API calls based on the provided Artifact Registry path.
        Example: For base_path 'us-docker.pkg.dev/my-project/my-repo',
        the returned URL would be 'https://region-domain-docker.pkg.dev/v2/my-project/my-repo'

    Raises:
        ValueError: If the input base_path is not in the expected format.
    """
    logger.debug(
        f"Trying to parse a DockerHub Google Artifact Registry internal base path {base_path=}"
    )
    # Split base path into region-domain, project, and repository
    try:
        region_domain, project, repository = base_path.split("/")
    except ValueError:
        raise ValueError(
            "Invalid Artifact Registry path format. Expected format: 'region-domain/project/repository'"
        )

    # Construct and return the base URL for DockerHub proxy API calls
    parsed_dockerhub_proxy_api_url = (
        f"https://{region_domain}/v2/{project}/{repository}"
    )
    logger.debug(
        f"Returning parsed DockerHub Google Artifact Registry API: {parsed_dockerhub_proxy_api_url=}"
    )
    return parsed_dockerhub_proxy_api_url


def get_registry_api_url(registry: str, default_registry: str) -> str:
    """
    Determine the appropriate registry API URL based on the environment and provided parameters.

    This function checks if the code is running in a GitLab CI environment and if a custom Docker.io URL is set.
    If both conditions are true, it uses the custom Docker.io URL. Otherwise, it falls back to the provided
    registry or the default registry.

    Args:
        registry (str): The registry URL provided by the user.
        default_registry (str): The default registry URL to use if no custom URL is provided.

    Returns:
        str: The determined registry API URL to use for Docker operations.
    """
    logger.debug(f"dockerhub_client | {IS_CONTENT_GITLAB_CI=}, {DOCKER_IO=}")
    if IS_CONTENT_GITLAB_CI and DOCKER_IO:
        try:
            logger.debug(
                "Running in a GitLab CI environment with custom DOCKER_IO environment variable, Trying to prase a DockerHub Google Artifact Registry from DOCKER_IO environment variable."
            )
            if parsed_dockerhub_proxy_api_url := get_dockerhub_artifact_registry_url(
                DOCKER_IO
            ):
                logger.debug(f"Successfully parsed {parsed_dockerhub_proxy_api_url=}")
                return parsed_dockerhub_proxy_api_url
            else:
                logger.debug(
                    "Could not parse a valid API URL from the DOCKER_IO environment variable."
                )
        except Exception as e:
            logger.debug(
                f"Could not parse a valid API URL from the DOCKER_IO environment variable, Error: {str(e)} "
            )

    logger.debug(f"using provided or default registry, {default_registry=}")
    return registry or default_registry


def get_gcloud_access_token() -> Optional[str]:
    """
    Retrieves a Google Cloud access token using environment credentials.

    This method attempts to obtain credentials from the environment and use them
    to retrieve a valid Google Cloud access token. If successful, it returns the
    token as a string. If unsuccessful, it returns None.

    Returns:
        str | None: The Google Cloud access token if successful, None otherwise.

    Raises:
        Exception: Any exception that occurs during the token retrieval process
                   is caught and logged, but not re-raised.
    """
    try:
        logger.debug("Trying to retrieve a Google Cloud access token.")
        # Automatically obtain credentials from the environment
        credentials, project_id = google.auth.default()

        # Refresh the token if needed (ensures the token is valid)
        credentials.refresh(Request())
        # Extract the access token
        access_token = credentials.token
        if access_token:
            logger.debug(
                f"Successfully obtained Google Cloud access token, {project_id=}."
            )
            return access_token
        else:
            logger.debug("Failed to obtain Google Cloud access token.")
            return None
    except Exception as e:
        logger.debug(f"Failed to get access token: {str(e)}")
        return None


def iso8601_to_datetime_str(iso8601_time: str) -> str:
    """
    Normalizes ISO 8601 datetime string to expected format.

    Args:
        iso8601_datetime_str (str): An ISO 8601 datetime string in the format %Y-%m-%dT%H:%M:%S.%fZ.

    Returns:
        str: A ISO 8601 datetime string in the format %Y-%m-%dT%H:%M:%S.%fZ with microseconds precision.

    Details:
    Python's datetime module supports up to microseconds precision (six decimal places in the seconds fraction (e.g., 0.123456 seconds).
    While iso8601 can support up to nanoseconds precision (nine decimal places in the seconds fraction (e.g., 0.123456789 seconds)).
    """
    # In case the time format is ISO 8601 - ISO supports 9 digits while datetime in python supports only 6,
    if "." in iso8601_time:
        timestamp_without_nanoseconds, nanoseconds = iso8601_time.rsplit(
            ".", maxsplit=1
        )
        fractional = nanoseconds.rstrip("Z")[:6]  # Keep only the first 6 digits.
        iso8601_time = f"{timestamp_without_nanoseconds}.{fractional}Z"
    return iso8601_time
