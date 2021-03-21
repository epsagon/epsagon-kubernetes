"""
Common and builtin fixtures & utilities
"""
import asyncio
import yaml
import time
from datetime import datetime, timedelta
import pytest
from kubernetes_asyncio import config
from kubernetes_asyncio import client
from kubernetes_asyncio import utils


def default_cluster_agent_deployment():
    """ Default cluster agent deployment """
    labels = {
        'app': 'epsagon-cluster-agent'
    }
    return client.V1Deployment(
        api_version='apps/v1',
        kind='Deployment',
        metadata=client.V1ObjectMeta(name='cluster-agent', namespace='epsagon-monitoring'),
        spec=client.V1DeploymentSpec(
            selector=client.V1LabelSelector(
                match_labels=labels.copy()
            ),
            replicas=1,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels.copy()),
                spec=client.V1PodSpec(
                    service_account_name='cluster-agent',
                    containers=[
                        client.V1Container(
                            name='cluster-agent',
                            image='epsagon/cluster-agent:test',
                            # required for pulling from the docker local loaded images
                            # and not from Epsagon remote hub
                            image_pull_policy='Never',
                            env=[
                                client.V1EnvVar(name='EPSAGON_TOKEN', value='123'),
                                client.V1EnvVar(name='EPSAGON_CLUSTER_NAME', value='test'),
                                client.V1EnvVar(name='EPSAGON_DEBUG', value='false'),
                                client.V1EnvVar(name='EPSAGON_COLLECTOR_URL', value='http://localhost:5000'),
                            ]
                        ),
                    ]
                ),
            ),
        ),
    )


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
        self.apps_api_client = client.AppsV1Api(api_client=api_client)
        self.api_client = self.apps_api_client.api_client

    async def install_epsagon_role(self):
        """ Installs the Epsagon role required for the cluster agent """
        await utils.create_from_yaml(self.api_client, '../../epsagon_role.yaml', namespace="epsagon-monitoring")

    async def install_cluster_agent(self, agent_deployment: client.V1Deployment):
        """ Installs the cluster agent """
        await self.apps_api_client.create_namespaced_deployment(
            agent_deployment.metadata.namespace,
            agent_deployment
        )

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
            if ready_replicas and ready_replicas > 0:
                print(ready_replicas)
                return
            time.sleep(2)
            end = datetime.now()

        raise Exception("Cluster agent pod failed to start")

    async def install_all(
            self,
            agent_deployment=None,
            wait_for_agent_pod_initialization=True,
    ):
        """
        Installs the cluster agent.
        """
        await self.install_epsagon_role()
        agent_deployment = (
            agent_deployment
            if agent_deployment
            else default_cluster_agent_deployment()
        )
        await self.install_cluster_agent(agent_deployment)
        deployment_name = agent_deployment.metadata.name
        deployment_namespace = agent_deployment.metadata.namespace
        if wait_for_agent_pod_initialization:
            await self._wait_for_deployment_pod(deployment_name, deployment_namespace)


