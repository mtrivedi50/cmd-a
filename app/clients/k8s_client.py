import asyncio
import base64
import logging
from pathlib import Path
from typing import Any

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from pydantic import SecretStr

from app.db.models.choices import (
    ExecutionRole,
    IntegrationStatus,
    IntegrationType,
    KubernetesResourceType,
)
from app.settings import Settings

logger = logging.getLogger(__name__)


# Kubernetes config
config.incluster_config.load_incluster_config()


class KubernetesOperator:
    """
    Class for altering, managing, and otherwise interacting with Kubernetes resources.
    Largely designed for inheritance, though can certainly be used by itself.
    """

    core_api: client.CoreV1Api
    apps_api: client.AppsV1Api
    batch_api: client.BatchV1Api
    rbac_authorization_api: client.RbacAuthorizationV1Api

    def __init__(self):
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.batch_api = client.BatchV1Api()
        self.rbac_authorization_api = client.RbacAuthorizationV1Api()

    @staticmethod
    def create_integration_execution_role_name(
        integration_type: IntegrationType, execution_role: ExecutionRole
    ):
        """
        Returns a name in the form:

            `<integration_type>-<execution_role>`

        Where:
        - `integration_type` is one of: `slack`, `jira`, `notion`, `github`
        - `execution_role` is one of: `scheduler`, `worker`

        Used for a variety of different things, e.g., label selectors, container names.
        """
        return f"{integration_type}-{execution_role}"

    def create_resource_name(
        self,
        integration_type: IntegrationType,
        execution_role: ExecutionRole,
        resource_type: KubernetesResourceType,
    ):
        """
        Resource names are referenced throughout this module and others. This is a
        simple function that standardizes how we create resource names. This prevents us
        from having to hardcode things. Returns a name in the form:

            `<integration_type>-<execution_role>-<resource_type>`

        Where:
        - `integration_type` is one of: `slack`, `jira`, `notion`, `github`
        - `execution_role` is one of: `scheduler`, `worker`
        - `resource_type` is one of: `deployment`, `cronjob`, `pod`, `service`
        """
        return f"{self.create_integration_execution_role_name(integration_type, execution_role)}-{resource_type}"

    @staticmethod
    def create_main_resource_metadata(
        namespace: str,
        resource_name: str,
    ) -> client.V1ObjectMeta:
        return client.V1ObjectMeta(
            name=resource_name,
            namespace=namespace,
            labels={"app": "main"},
        )

    @staticmethod
    def get_name_from_metadata(
        resp: Any,
    ) -> str:
        """Helper function for mypy"""
        if not hasattr(resp, "metadata"):
            raise Exception("Object does not have metadata")
        if not isinstance(resp.metadata, client.V1ObjectMeta):
            raise Exception("Object metadata is not of type `V1ObjectMeta`")
        if not resp.metadata.name:
            raise Exception(
                f"V1ObjectMeta {resp.metadata} does not have a name.".strip()
            )
        return resp.metadata.name

    def create_deployment_label_selector(
        self,
        integration_type: IntegrationType,
        execution_role: ExecutionRole,
    ) -> dict[str, str]:
        """
        For the deployment label selector and pod template metadata. Returns a
        dictionary with one key: `app` that maps to a name in the form:

            `<integration_type>-<execution_role>`

        Where:
        - `integration_type` is one of: `slack`, `jira`, `notion`, etc.
        - `execution_role` is one of: `scheduler`, `worker`
        """
        return {
            "app": self.create_integration_execution_role_name(
                integration_type, execution_role
            )
        }

    def list_namespaces(self) -> list[str]:
        namespaces = self.core_api.list_namespace()
        namespaces_list: list[str] = []
        for ns in namespaces.items:
            if ns.metadata and ns.metadata.name:
                namespaces_list.append(ns.metadata.name)
        return namespaces_list

    def create_namespace(self, namespace: str) -> client.V1Namespace:
        # If namespace exists, just return it.
        namespaces: client.V1NamespaceList = self.core_api.list_namespace()
        if namespaces.items:
            for ns in namespaces.items:
                # For mypy
                if not isinstance(ns, client.V1Namespace):
                    raise Exception("Unrecognized type in V1NamespaceList!")

                namespace_name = self.get_name_from_metadata(ns)
                if namespace_name == namespace:
                    return ns

        return self.core_api.create_namespace(
            body=client.V1Namespace(
                api_version="v1",
                kind="Namespace",
                metadata=client.V1ObjectMeta(name=namespace),
            )
        )

    @staticmethod
    def create_env_vars_from_settings(
        exclude: list[str] | None = None,
    ) -> list[client.V1EnvVar]:
        env_var_list: list[client.V1EnvVar] = []
        for env_var, env_var_value in Settings.model_dump().items():
            # Skip variables to exclude
            if exclude and env_var in exclude:
                continue

            # Skip paths
            elif isinstance(env_var_value, Path):
                continue

            # Unnest nested environment variables. Assume only one level of nesting.
            elif isinstance(env_var_value, dict):
                for nested_env_var, nested_env_var_value in env_var_value.items():
                    if nested_env_var_value:
                        env_var_list.append(
                            client.V1EnvVar(
                                name=f"{env_var}__{nested_env_var.upper()}",
                                value=(
                                    nested_env_var_value.get_secret_value()
                                    if isinstance(nested_env_var_value, SecretStr)
                                    else str(nested_env_var_value)
                                ),
                            )
                        )
            else:
                if env_var_value:
                    env_var_list.append(
                        client.V1EnvVar(
                            name=env_var,
                            value=(
                                env_var_value.get_secret_value()
                                if isinstance(env_var_value, SecretStr)
                                else str(env_var_value)
                            ),
                        )
                    )
        return env_var_list

    def get_configmap_data(
        self,
        configmap_name: str,
        namespace: str,
    ) -> dict[str, str]:
        configmap = self.core_api.read_namespaced_config_map(
            name=configmap_name, namespace=namespace
        )
        return configmap.data or {}

    def copy_configmap(
        self,
        configmap_name: str,
        target_namespace: str,
        source_namespace: str = "default",
    ):
        """Copy ConfigMap from default namespace to a users' namespace. Used to
        propagate service names to the users' namespaces.
        """
        target_configmaps: client.V1ConfigMapList = (
            self.core_api.list_namespaced_config_map(namespace=target_namespace)
        )
        if target_configmaps.items:
            for target_configmap in target_configmaps.items:
                # For mypy
                if not isinstance(target_configmap, client.V1ConfigMap):
                    raise Exception("Unrecognized type in V1ConfigMapList!")
                target_configmap_name = self.get_name_from_metadata(target_configmap)
                if target_configmap_name == configmap_name:
                    return target_configmap

        # If we've reached this stage, then the ConfigMap does not exist in the target
        # database.
        configmap: client.V1ConfigMap = self.core_api.read_namespaced_config_map(
            name=configmap_name, namespace=source_namespace
        )
        if not configmap.data and not configmap.binary_data:
            raise Exception(f"ConfigMap {configmap_name} does not have any data!")

        # Create a new ConfigMap in the target namespace
        new_configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(name=configmap_name),
            data=configmap.data if configmap.data else {},
            binary_data=configmap.binary_data if configmap.binary_data else {},
        )
        resp = self.core_api.create_namespaced_config_map(
            namespace=target_namespace, body=new_configmap
        )
        return resp

    def copy_secret(
        self, secret_name: str, target_namespace: str, source_namespace: str = "default"
    ) -> client.V1Secret:
        """Copy Secret from default namespace to a users' namespace. Used to
        propagate service names to the users' namespaces.
        """
        secret_list: client.V1SecretList = self.core_api.list_namespaced_secret(
            namespace=target_namespace
        )
        if secret_list.items:
            for target_secret in secret_list.items:
                # For mypy
                if not isinstance(target_secret, client.V1Secret):
                    raise Exception("Unrecognized type in V1SecretList!")
                target_secret_name = self.get_name_from_metadata(target_secret)
                if target_secret_name == secret_name:
                    return target_secret

        # If we've reached this stage, then the ConfigMap does not exist in the target
        # database.
        secret: client.V1Secret = self.core_api.read_namespaced_secret(
            name=secret_name, namespace=source_namespace
        )
        if not secret.data and not secret.string_data:
            raise Exception(f"Secret {secret_name} does not have any data!")

        # Create a new ConfigMap in the target namespace
        new_secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name=secret_name),
            data=secret.data if secret.data else {},
            string_data=secret.string_data if secret.string_data else {},
            type=secret.type,
        )
        resp = self.core_api.create_namespaced_secret(
            namespace=target_namespace, body=new_secret
        )
        return resp

    def create_service_account(
        self, namespace: str, service_account_name: str
    ) -> client.V1ServiceAccount:
        # See if service account already exists
        service_accounts: client.V1ServiceAccountList = (
            self.core_api.list_namespaced_service_account(namespace=namespace)
        )
        if service_accounts.items:
            for svc_account in service_accounts.items:
                # For mypy
                if not isinstance(svc_account, client.V1ServiceAccount):
                    raise Exception("Unrecognized type in V1ServiceAccountList!")

                svc_account_name = self.get_name_from_metadata(svc_account)
                if svc_account_name == service_account_name:
                    return svc_account

        # If we've reach this stage, then the service account does not exist
        resp = self.core_api.create_namespaced_service_account(
            namespace=namespace,
            body=client.V1ServiceAccount(
                metadata=client.V1ObjectMeta(name=service_account_name)
            ),
        )
        return resp

    def create_all_access_rbac_role(
        self,
        namespace: str,
        api_groups: list[str] | None = None,
        resources: list[str] | None = None,
        verbs: list[str] | None = None,
    ) -> client.V1Role:
        """
        Create a role with broad permissions to manipulate all resources across all APIs
        in the namespace
        """
        # We could probably create a cluster role and use that instead of creating an
        # individual role for each namespace. But whatever...

        #  Defaults
        api_groups = (
            ["", "batch", "apps", "rbac.authorization.k8s.io"]
            if not api_groups
            else api_groups
        )
        resources = ["*"] if not resources else resources
        verbs = ["*"] if not verbs else verbs

        new_role_name = "all-resources-all-actions"
        existing_roles: client.V1RoleList = (
            self.rbac_authorization_api.list_namespaced_role(namespace=namespace)
        )

        # If there are no cluster roles (which should never be the case), then ignore.
        # Otherwise, iterate through the cluster role and see if
        # `all-resources-all-actions` exists.
        if existing_roles.items:
            for role in existing_roles.items:
                # For mypy
                if not isinstance(role, client.V1Role):
                    raise Exception("Unrecognized type in V1RoleList!")

                # Return cluster role if it already exists
                role_name = self.get_name_from_metadata(role)
                if role_name == new_role_name:
                    return role

        # If we've reached this code, the cluster role does not exist.
        resp: client.V1Role = self.rbac_authorization_api.create_namespaced_role(
            namespace=namespace,
            body=client.V1Role(
                api_version="rbac.authorization.k8s.io/v1",
                metadata=client.V1ObjectMeta(name=new_role_name),
                rules=[
                    client.V1PolicyRule(
                        api_groups=api_groups,
                        resources=resources,
                        verbs=verbs,
                    )
                ],
            ),
        )
        return resp

    def create_role_binding(
        self,
        namespace: str,
        service_account_name: str,
        role_name: str = "all-resources-all-actions",
    ) -> client.V1RoleBinding:
        """
        Bind ServiceAccount `service_account_name` to the permissions defined in Role
        `role_name`.
        """
        role_binding_name = f"{role_name}-binding"

        role_bindings = self.rbac_authorization_api.list_namespaced_role_binding(
            namespace=namespace
        )
        if role_bindings.items:
            # For mypy
            for role_binding in role_bindings.items:
                if not isinstance(role_binding, client.V1RoleBinding):
                    raise Exception("Unrecognized type in V1RoleBindingList!")

                # Role reference must match the inputted role name
                if (
                    self.get_name_from_metadata(role_binding) == role_binding_name
                    and role_binding.role_ref
                    and role_binding.role_ref.kind == "Role"
                    and role_binding.role_ref.name == role_name
                ):
                    # We have to do these annoying ifs because the API client's return
                    # type can be None, and mypy throws a fit if we don't have them...
                    if role_binding.subjects:
                        for subject in role_binding.subjects:
                            # More stuff for mypy...
                            if not isinstance(subject, client.RbacV1Subject):  # type: ignore
                                raise Exception(
                                    "Unrecognized subject type in V1RoleBinding!"
                                )

                            # If the current subject exists, then just return
                            if (
                                subject.kind
                                and subject.kind == "ServiceAccount"
                                and subject.name
                                and subject.name == service_account_name
                            ):
                                return role_binding

                        # Otherwise, add another subject to the binding
                        new_subject = client.RbacV1Subject(  # type: ignore
                            kind="ServiceAccount",
                            name=service_account_name,
                            api_group="",
                        )
                        resp = (
                            self.rbac_authorization_api.patch_namespaced_role_binding(
                                name=role_binding_name,
                                namespace=namespace,
                                body={
                                    "subjects": role_binding.subjects + [new_subject]
                                },
                            )
                        )
                        return resp

        # If we've reach this stage, then no role binding exists
        resp = self.rbac_authorization_api.create_namespaced_role_binding(
            namespace=namespace,
            body=client.V1RoleBinding(
                metadata=client.V1ObjectMeta(name=role_binding_name),
                role_ref=client.V1RoleRef(
                    kind="Role", name=role_name, api_group="rbac.authorization.k8s.io"
                ),
                subjects=[
                    client.RbacV1Subject(  # type: ignore
                        kind="ServiceAccount",
                        name=service_account_name,
                        api_group="",
                    )
                ],
            ),
        )
        return resp

    def destroy_namespace(self, namespace: str) -> None:
        # We don't need this deletion operation to be blocking...
        self.core_api.delete_namespace(name=namespace, async_req=True)  # type: ignore
        return None

    def destroy_deployment(
        self, namespace: str, deployment_name: str, **kwargs
    ) -> None:
        try:
            self.apps_api.delete_namespaced_deployment(
                name=deployment_name, namespace=namespace, **kwargs
            )
        except ApiException as e:
            if "Not Found" not in str(e.reason):
                raise
        return None

    def destroy_cronjob(self, namespace: str, cronjob_name: str, **kwargs) -> None:
        try:
            self.batch_api.delete_namespaced_cron_job(
                name=cronjob_name, namespace=namespace, **kwargs
            )
        except ApiException as e:
            if "Not Found" not in str(e.reason):
                raise
        return None

    def create_or_update_secret(
        self,
        namespace: str,
        secret_name: str,
        secret_data: dict[str, Any],
    ) -> client.V1Secret:
        current_namespaced_secrets = self.core_api.list_namespaced_secret(
            namespace=namespace
        )
        current_namespaced_secret_names = [
            self.get_name_from_metadata(resource)
            for resource in current_namespaced_secrets.items
        ]
        secret_data_encoded = {
            k: base64.b64encode(v.encode("utf-8")).decode("utf-8")
            for k, v in secret_data.items()
        }
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=secret_name,
            ),
            type="Opaque",
            data=secret_data_encoded,
        )
        res = (
            self.core_api.patch_namespaced_secret(
                name=secret_name, namespace=namespace, body=body
            )
            if secret_name in current_namespaced_secret_names
            else self.core_api.create_namespaced_secret(namespace=namespace, body=body)
        )
        return res

    def read_namespaced_secret(
        self, namespace: str, secret_name: str
    ) -> dict[str, Any]:
        secret: client.V1Secret = self.core_api.read_namespaced_secret(
            name=secret_name, namespace=namespace
        )
        if not secret.data:
            raise ValueError(
                f"Secret `{secret_name}` in {namespace} namespace does not have any data."
            )
        return {
            k: base64.b64decode(v.encode("utf-8")).decode("utf-8")
            for k, v in secret.data.items()
        }

    def destroy_secret(
        self,
        namespace: str,
        secret_name: str,
    ) -> None:
        self.core_api.delete_namespaced_secret(  # type: ignore
            name=secret_name, namespace=namespace, async_req=True
        )

    def async_delete_jobs(self, namespace: str, pattern: str) -> None:
        jobs: client.V1JobList = self.batch_api.list_namespaced_job(namespace=namespace)
        if jobs.items:
            for job in jobs.items:
                # For mypy
                if not isinstance(job, client.V1Job):
                    raise Exception("Unrecognized type in V1JobList!")

                job_name = self.get_name_from_metadata(job)
                if pattern in job_name:
                    try:
                        self.batch_api.delete_namespaced_job(  # type: ignore
                            name=job_name, namespace=namespace, async_req=True
                        )
                    except ApiException as e:
                        if "Not Found" not in str(e.reason):
                            continue

    def async_delete_cron_jobs(self, namespace: str, pattern: str) -> None:
        cron_jobs: client.V1CronJobList = self.batch_api.list_namespaced_cron_job(
            namespace=namespace
        )
        if cron_jobs.items:
            for cron_job in cron_jobs.items:
                # For mypy
                if not isinstance(cron_job, client.V1CronJob):
                    raise Exception("Unrecognized type in V1CronJobList!")

                cron_job_name = self.get_name_from_metadata(cron_job)
                if pattern in cron_job_name:
                    try:
                        self.batch_api.delete_namespaced_cron_job(  # type: ignore
                            name=cron_job_name, namespace=namespace, async_req=True
                        )
                    except ApiException as e:
                        if "Not Found" not in str(e.reason):
                            continue

    def async_delete_pods(self, namespace: str, pattern: str) -> None:
        pods: client.V1PodList = self.core_api.list_namespaced_pod(namespace=namespace)
        if pods.items:
            for pod in pods.items:
                # For mypy
                if not isinstance(pod, client.V1Pod):
                    raise Exception("Unrecognized type in V1PodList!")

                pod_name = self.get_name_from_metadata(pod)
                if pattern in pod_name:
                    try:
                        self.core_api.delete_namespaced_pod(  # type: ignore
                            name=pod_name, namespace=namespace, async_req=True
                        )
                    except ApiException as e:
                        if "Not Found" not in str(e.reason):
                            continue

    def get_jobs_matching_pattern(
        self,
        namespace: str,
        pattern: str,
    ) -> dict[str, client.V1Job]:
        """Get namespaced jobs whose name matches the inputted pattern."""
        matching_job_name_map: dict[str, client.V1Job] = {}
        jobs: client.V1JobList = self.batch_api.list_namespaced_job(namespace=namespace)
        if jobs.items:
            for job in jobs.items:
                # For mypy
                if not isinstance(job, client.V1Job):
                    raise Exception("Unrecognized type in V1JobList!")

                job_name = self.get_name_from_metadata(job)
                if pattern in job_name:
                    matching_job_name_map[job_name] = job
        return matching_job_name_map

    def check_job_status(
        self,
        namespace: str,
        job_name: str,
    ) -> IntegrationStatus:
        """
        Check if a job is complete with failure detection.
        """
        flag_is_complete: bool = False
        flag_is_failed: bool = False
        try:
            job: client.V1Job = self.batch_api.read_namespaced_job(
                name=job_name,
                namespace=namespace,
            )
            status: client.V1JobStatus | None = job.status
            if status:
                conditions: list[client.V1JobCondition] | None = status.conditions

                # Per the documentation: A job is considered finished when it is in a
                # terminal condition, either "Complete" or "Failed". A Job cannot have both
                # the "Complete" and "Failed" conditions
                if conditions:
                    for cond in conditions:
                        flag_is_complete = (
                            cond.status is not None  # for mypy
                            and cond.type is not None  # for mypy
                            and cond.status == "True"
                            and cond.type == "Complete"
                        )
                        flag_is_failed = (
                            cond.status is not None  # for mypy
                            and cond.type is not None  # for mypy
                            and cond.status == "True"
                            and cond.type == "Failed"
                        )

            if flag_is_complete:
                return IntegrationStatus.SUCCESS
            elif flag_is_failed:
                return IntegrationStatus.FAILED
            else:
                return IntegrationStatus.RUNNING
        except ApiException as e:
            # If the job isn't found, then it succeeded and was deleted. We only delete
            # successful jobs, not failed jobs.
            if "Not Found" in str(e):
                return IntegrationStatus.SUCCESS
            else:
                raise

    async def verify_deployment(
        self, name: str, namespace: str, expected_replicas: int, timeout: int = 300
    ) -> bool:
        """
        Verify that Deployment has the correct number of ready replicas
        """
        try:
            start_time = asyncio.get_event_loop().time()
            while True:
                try:
                    deployment: client.V1Deployment = (
                        self.apps_api.read_namespaced_deployment_status(
                            name=name, namespace=namespace
                        )
                    )
                    if (
                        deployment.status
                        and deployment.status.ready_replicas == expected_replicas
                    ):
                        logger.info(
                            f"Deployment {name} has {expected_replicas} ready replicas"
                        )
                        return True

                    # For mypy
                    ready_replicas = 0
                    if (
                        deployment.status
                        and deployment.status.ready_replicas is not None
                    ):
                        ready_replicas = deployment.status.ready_replicas

                    logger.info(
                        f"Waiting for {name} replicas to be ready. "
                        f"Current: {ready_replicas}, "
                        f"Expected: {expected_replicas}"
                    )

                except ApiException:
                    pass

                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.error(f"Timeout waiting for {name} replicas to be ready")
                    return False

                await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error verifying deployment {name}: {str(e)}")
            return False
