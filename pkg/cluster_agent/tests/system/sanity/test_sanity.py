"""
System sanity tests
"""
import asyncio
import pytest
import conftest


@pytest.fixture(scope='session', autouse=True)
async def install_agent():
    installer = conftest.ClusterAgentInstaller()
    await installer.install_all()

@pytest.mark.asyncio
async def test_sanity():
    """
    A placeholder test - ran by CICD, used to test the agent pod is
    running successfully.
    """
    pass
