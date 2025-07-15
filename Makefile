
.PHONY: install-deps setup-precommit-hooks setup alembic-make-migrations alembic-migrate setup-skaffold-cluster use-skaffold-docker-context dev build-docling-image build-backend-image update-docling-image-version

#########
# Setup #
#########

install-deps:
	brew install uv
	uv sync
	cd frontend && npm install

setup-precommit-hooks:
	uv run pre-commit install
	cd frontend && npx husky init
	sed -i .bak '/npm test/d' frontend/.husky/pre-commit
	echo "cd frontend && npx lint-staged" >> frontend/.husky/pre-commit
	echo "cd .. && uv run pre-commit run" >> frontend/.husky/pre-commit
	npx husky frontend/.husky
	@if [ -d .husky ]; then \
		rm -rf .husky; \
	fi
	mv frontend/.husky .
	rm .husky/pre-commit.bak
	git config core.hooksPath .husky/_

setup-dev-env: install-deps setup-precommit-hooks


##############
# Migrations #
##############

alembic-make-migrations:
	./alembic/make-migrations.sh

alembic-migrate:
	uv run alembic upgrade head


###############
# Dev targets #
###############

setup-skaffold-cluster:
	brew install minikube skaffold
	minikube start --cpus 4 --memory 4096;
	skaffold config set --global local-cluster true;


######################
# Kubernetes targets #
######################

build-docling-image:
	docker buildx build -t mtrivedi50/cmd-a-docling:$(VERSION) -f manifests/docker/Dockerfile.docling . --platform linux/amd64; \
	docker push mtrivedi50/cmd-a-docling:$(VERSION)

build-backend-image:
	docker buildx build -t mtrivedi50/cmd-a:$(VERSION) -f manifests/docker/Dockerfile.main . --platform linux/amd64; \
	docker push mtrivedi50/cmd-a:$(VERSION)

update-docling-image-version:
	sed -i 's|"__DO_NOT_EDIT__"|"$(VERSION)"|g' app/processors/base/worker.py; \
	sed -i 's|"__DO_NOT_EDIT__"|"$(VERSION)"|g' app/rest_api/integrations.py; \
	sed -i 's|"__DO_NOT_EDIT__"|"$(VERSION)"|g' app/rest_api/integrations.py;
