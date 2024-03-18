"""
API Swagger Modifier.
Only use this for documentation.
"""

import os
import json

from fastapi import FastAPI


class ApiModifier:
    """
    A class for modifying and saving OpenAPI configuration for a FastAPI app.
    """

    def __init__(self, app: FastAPI):
        self.app = app
        self.api_config = self.app.openapi()

    def add_meta_data(self, title: str = None, version: str = None) -> None:
        """
        Add meta data to show in the swagger page.

        Args:
            title: Title of FastAPI app.
            version: Version of FastAPI app.
        """

        # Set metadata
        if title:
            self.api_config["info"]["title"] = title

        if version:
            self.api_config["info"]["version"] = version

    def _save_openapi_to_json(
        self, path: str = "", config_name: str = "openapi.json"
    ) -> None:
        """
        Saves OpenAPI data to a JSON file.

        Args:
            path: The path where the JSON file will be saved. Defaults to the current directory.
            config_name: The name of the JSON file. Defaults to 'openapi.json'.
        """
        # Create folder if it doesn't exist
        if not os.path.exists(path):
            os.makedirs(path)

        # Write JSON to file
        with open(path + config_name, "w") as file:
            json.dump(self.api_config, file, indent=2)

    def change_server_host(
        self, hosts: list[str], descriptions: list[str] = None
    ) -> None:
        """
        Change server in openapi_json to correspond with the server used for the FastAPI endpoint.

        Args:
            hosts: List of base URLs for the servers.
            descriptions: List of descriptions for the servers. Defaults to ['No description.'] * len(hosts).
        """
        if descriptions is None:
            descriptions = ["No description."] * len(hosts)
        assert len(hosts) == len(
            descriptions
        ), "The length of the host and description should be the same or descriptions should be left empty for no descriptions."

        # Load JSON string into a dictionary
        host_list = []
        for host, description in zip(hosts, descriptions):
            host_list.append({"url": host, "description": description})
        self.api_config["servers"] = host_list

    def save_openapi(
        self,
        path: str = "",
        config_name: str = "openapi.json",
        title: str = None,
        version: str = None,
        hosts: list[str] = None,
        descriptions: list[str] = None,
    ) -> None:
        """
        Saves and corrects the OpenAPI configuration as a JSON file.

        Args:
            path: Location to store the OpenAPI configuration.
            config_name: Name of the OpenAPI configuration file.
            title: Title of FastAPI app.
            version: Version of FastAPI app.
            hosts: List of base URLs for the servers.
            descriptions: List of descriptions for the servers. Defaults to None.
        """
        self.add_meta_data(title=title, version=version)
        if hosts:
            self.change_server_host(hosts, descriptions)

        self._save_openapi_to_json(path=path, config_name=config_name)
