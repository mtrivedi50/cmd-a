# Deployment steps

- Create a Kubernetes cluster on Digital Ocean.
- Create Digital Ocean token secret in `kube-system` namespace
```
kubectl apply -f token-secret.yaml
```
- Deploy Container Storage Interface (CSI) driver for Digital Ocean Block Storage. This creates the DO block storage class, which dynamically provisions persistent volumes when a persistent volume claim is made.
```
kubectl apply -f https://raw.githubusercontent.com/digitalocean/csi-digitalocean/master/deploy/kubernetes/releases/csi-digitalocean-v4.9.0/{crds.yaml,driver.yaml,snapshot-controller.yaml}
```
- Add bitnami Postgres chart
```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```
- Create Postgres persistent volume claim
```
kubectl apply -f postgres-pvc.yaml
```
- Install Postgres helm chart
```
helm install postgresdb bitnami/postgresql --set persistence.existingClaim=postgresql-postgres-pvc --set volumePermissions.enabled=true
```
- Install Redis helm chart
```
helm install redis bitnami/redis
```
- Create secrets for external clients
```
kubectl apply -f graphdb-secrets.yaml
kubectl apply -f mongodb-secrets.yaml
kubectl apply -f pinecone-secrets.yaml
```
- Create cluster role and config map.
```
kubectl apply -f cluster_role.yaml
kubectl apply -f config_map.yaml
```
- Deploy the backend server
```
cd .. && make build-backend-image NEW=<version>
```
- Install nginx controller
```
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace --set controller.publishService.enabled=true
```
- Deploy the frontend UI
```
cd .. && make build-frontend-image NEW=<version>
```
