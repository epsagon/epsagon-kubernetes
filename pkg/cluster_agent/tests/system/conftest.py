"""
Common and builtin fixtures & utilities
"""
import asyncio
import yaml
from typing import Dict
from datetime import datetime, timedelta
import pytest
from kubernetes_asyncio import config
from kubernetes_asyncio import client
from kubernetes_asyncio import utils

DEFAULT_CLUSTER_AGENT_DEPLOYMENT = {
    'apiVersion': 'apps/v1',
    'kind': 'Deployment',
    'metadata': {'name': 'agent-cluster-agent', 'namespace': 'epsagon-monitoring'},
    'spec': {
        'selector': {'matchLabels': {'app': 'epsagon-cluster-agent'}},
        'replicas': 1,
        'template': {
            'metadata': {'labels': {'app': 'epsagon-cluster-agent'}},
            'spec': {
                'serviceAccountName': 'cluster-agent',
                'containers': [
                    {
                        'name': 'cluster-agent',
                        'image': 'epsagon/cluster-agent:1.0.0',
                        # required for pulling from the docker local loaded images
                        # and not from Epsagon remote hub
                        'imagePullPolicy': 'Never',
                        'env': [
                            {'name': 'EPSAGON_TOKEN', 'value': '123'},
                            {'name': 'EPSAGON_CLUSTER_NAME', 'value': 'test'},
                            {'name': 'EPSAGON_DEBUG', 'value': 'false'},
                            {
                                'name': 'EPSAGON_COLLECTOR_URL',
                                'value': 'http://localhost:5000'
                            }
                        ]
                    }
                ]
            }
        }
    }
}

@pytest.fixture(scope='session')
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session', autouse=True)
async def load_cluster_config():
    """
    Loads the cluster config.
    Assumes `kubectl` is set to the environment test cluster.
    """
    await config.load_kube_config()


class ClusterAgentInstaller:
    """ Cluster agent installer """

    def __init__(self, api_client=None):
        self.api_client = api_client
        self.apps_api_client = client.AppsV1Api(api_client=self.api_client)

    def install_epsagon_role(self):
        """ Installs the Epsagon role required for the cluster agent """
        utils.create_from_yaml('../../epsagon_role.yaml')

    def _install_cluster_agent(self, agent_deployment: Dict):
        """ Installs the cluster agent """
        utils.create_from_dict(agent_deployment)

    async def _wait_for_deployment_pod(self, deployment_name: str, namespace: str):
        """
        Waits for one a pod of the given deployment to be ready
        """
        timeout = timedelta(seconds=10)
        start = datetime.now()
        end = datetime.now()
        while end - start < timeout:
            deployment = await self.apps_api_client.read_namespaced_deployment(
                deployment_name,
                namespace
            )
            ready_replicas = deployment.status.ready_replicas
            if ready_replicas > 0:
                print(ready_replicas)
                return
            time.sleep(2)

        raise Exception("Cluster agent pod failed to start")

    async def install_all(
            self,
            agent_deployment=None,
            wait_for_agent_pod_initialization=True,
    ):
        """
        Installs the cluster agent.
        """
        print("X")
        #self._install_epsagon_role()
        agent_deployment = (
            agent_deployment
            if agent_deployment
            else DEFAULT_CLUSTER_AGENT_DEPLOYMENT
        )
        #self._install_cluster_agent(agent_deployment)
        deployment_name = agent_deployment["metadata"]["name"]
        deployment_namespace = agent_deployment["metadata"]["namespace"]
        if wait_for_agent_pod_initialization:
            await self._wait_for_deployment_pod(deployment_name, deployment_namespace)


