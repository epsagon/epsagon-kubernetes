# pylint: disable=too-many-lines
"""
K8s cluster resources scanner
"""
import json
from typing import List, Tuple
import kubernetes
import urllib3
from requests import post, exceptions as requests_exceptions
from encoders import DateTimeEncoder

class ClusterScanner:
    """
    k8s resources scanner for a single cluster
    """

    def __init__(self, epsagon_token, api_client=None, timeout=None):
        """
        :param timeout: (Optional) cluster requests timeout (used only if client is not given)
        """
        self.epsagon_token = epsagon_token
        self.client = kubernetes.client.CoreV1Api()
        self.version_client = kubernetes.client.VersionApi()
        self.apps_api_client = kubernetes.client.AppsV1Api()

    def _scan_k8s_resources(self) -> Tuple[List]:
        """
        Scans target k8s cluster for different k8s resources
        """
        deployments = self.scan_deployments()
        pods = self.scan_pods()
        amazon_cw_data = self.scan_amazon_cw_configmap()
        return deployments, pods, amazon_cw_data

    def scan(self, update_time):
        """
        Scan cluster resources
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
                deployments, pods, amazon_cw_data = self._scan_k8s_resources()
        except (
            urllib3.exceptions.ConnectionError,
            requests_exceptions.ConnectionError,
        ):
            pass

        # send all data
        if nodes:
            data = {
                "cluster_version": cluster_version,
                "resources": [item.to_dict() for item in nodes + pods + deployments],
            }
            if amazon_cw_data:
                data["amazon_cw_configmap"] = amazon_cw_data
        else:
            data = {}
        # add token
        post(
            "",
            data=json.dumps(data, cls=DateTimeEncoder),
            headers={'Content-Type': 'application/json'}
        )


    def scan_version(self):
        """
        Scan the cluster version
        """
        return self.version_client.get_code().git_version

    def scan_amazon_cw_configmap(self):
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
        get k8s nodes form `cluster` and save them to db
        :param update_time: the time to calculate expiration from
        """
        nodes = self.client.list_node().items
        type(self)._set_kind_to_resources(nodes, "node")
        return nodes

    def scan_deployments(self):
        """
        gets k8s deployments from `cluster`, and saves them to the db
        """
        deployments = (
            self.apps_api_client.list_deployment_for_all_namespaces().items
        )
        type(self)._set_kind_to_resources(deployments, "deployment")
        return deployments

    def scan_pods(self):
        """
        gets k8s pods from `cluster`, and saves them to the db
        :param update_time: the time to calculate expiration from
        :param deployments: to set pod deployment by
        """
        pods = self.client.list_pod_for_all_namespaces().items
        type(self)._set_kind_to_resources(pods, "pod")
        return pods
