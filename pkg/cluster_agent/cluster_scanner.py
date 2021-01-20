# pylint: disable=too-many-lines
"""
K8s cluster resources scanner
"""
import json
import logging
from typing import List, Tuple
import kubernetes
import urllib3
from requests import post, exceptions as requests_exceptions
from requests.auth import HTTPBasicAuth
from encoders import DateTimeEncoder

class ClusterScanner:
    """
    k8s resources scanner
    """

    def __init__(self, epsagon_token, cluster_name, api_client=None, timeout=None):
        self.epsagon_token = epsagon_token
        self.cluster_name = cluster_name
        self.client = kubernetes.client.CoreV1Api(api_client=api_client)
        self.version_client = kubernetes.client.VersionApi(api_client=api_client)
        self.apps_api_client = kubernetes.client.AppsV1Api(api_client=api_client)

    def scan(self, update_time):
        """
        Scans the cluster
        """
        pods = []
        deployments = []
        nodes = []
        amazon_cw_data = {}
        cluster_version = None
        try:
            cluster_version = self.scan_version()
            nodes = self.scan_nodes()
            # we assume a target k8s cluster must have at least one worker node
            if nodes:
                deployments, pods = self.scan_deployments(), self.scan_pods()
            amazon_cw_data = self.scan_amazon_cw_configmap()
        except (
            urllib3.exceptions.ConnectionError,
            requests_exceptions.ConnectionError,
        ):
            pass

        data = {
            "update_time": update_time,
            "epsagon_token": self.epsagon_token,
            "cluster": {
                "name": self.cluster_name,
            }
        }
        if cluster_version:
            data["cluster"]["version"] = cluster_version
        if nodes:
            data["resources"] = [item.to_dict() for item in nodes + pods + deployments]
        if amazon_cw_data:
            data["cw_configmap"] = amazon_cw_data

        post(
            "https://dev.collector.epsagon.com/resources/v1",
            data=json.dumps(data, cls=DateTimeEncoder),
            headers={'Content-Type': 'application/json'},
            auth=HTTPBasicAuth(self.epsagon_token, ''),
        )


    def scan_version(self):
        """
        Gets the cluster version
        """
        return self.version_client.get_code().git_version

    def scan_amazon_cw_configmap(self):
        """
        Gets the aws CW configmap, if exists
        """
        data = {}
        configmap_list = self.client.list_namespaced_config_map("amazon-cloudwatch", field_selector="metadata.name=cluster-info")
        if configmap_list.items:
            cw_configmap = configmap_list.items[0].data
            if cw_configmap:
                data["cw_cluster_name"] = cw_configmap["cluster.name"]
                data["cw_region"] = cw_configmap["logs.region"]
        return data

    @staticmethod
    def _set_resource_kind(resource, kind):
        resource.kind = kind

    @staticmethod
    def _set_kind_to_resources(resources, kind):
        for resource in resources:
            ClusterScanner._set_resource_kind(resource, kind)

    def scan_nodes(self):
        """
        Scans the cluster nodes
        """
        nodes = self.client.list_node().items
        type(self)._set_kind_to_resources(nodes, "node")
        return nodes

    def scan_deployments(self):
        """
        Scans the cluster deployments
        """
        deployments = (
            self.apps_api_client.list_deployment_for_all_namespaces().items
        )
        type(self)._set_kind_to_resources(deployments, "deployment")
        return deployments

    def scan_pods(self):
        """
        Scans the cluster pods
        """
        pods = self.client.list_pod_for_all_namespaces().items
        type(self)._set_kind_to_resources(pods, "pod")
        return pods
