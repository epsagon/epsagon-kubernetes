<p align="center">
  <a href="https://epsagon.com" target="_blank" align="center">
    <img src="https://cdn2.hubspot.net/hubfs/4636301/Positive%20RGB_Logo%20Horizontal%20-01.svg" width="300">
  </a>
  <br />
</p>

# Epsagon Kubernetes Cluster Agent - System tests

To run the ckuster agent system tests, you need the kubectl context to be set to a
kubernetes cluster where the cluster agent is already installed on.
Those tests also run as part of the CICD by an workflow set for this repo. 
The workflow which already take care of the environment setup (using a Kind cluster).

## Prerequisites

*  A Kubernetes cluster environment with the Epsagon cluster agent installed on. The cluster can be also a Kind cluster or another non-real environment. The cluster version should be 1.16+.
* `kubectl` context to be set to your environment test cluster.
