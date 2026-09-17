.PHONY: inspect-cloud-account bootstrap-cloud-foundation check-cloud-foundation-script operations-outputs inspect-cloud-dns inspect-cloud-projects inspect-clerk inspect-vercel inspect-demo-prerequisites inspect-cache-image-sources inspect-container-engine publish-cache-images verify-demo-endpoints inspect-demo-build inspect-demo-serving inspect-demo-summary-errors inspect-demo-summary-queue demo-note inspect-demo-prerequisites-report test-onboarding inspect-project-routing

inspect-cloud-account:
	@set -e
	gcloud config list --format='json(core.account,auth.impersonate_service_account)' --quiet
	gcloud organizations list --format='json(name,displayName)' --quiet
	gcloud billing accounts list --filter='open=true' --format='json(name,displayName,open)' --quiet

bootstrap-cloud-foundation:
	@bash infrastructure/cli/provider/bootstrap-foundation $(ARGS)

check-cloud-foundation-script:
	@bash -n infrastructure/cli/provider/bootstrap-foundation

operations-outputs:
	@set -euo pipefail
	terraform -chdir=infrastructure/terraform/configurations/operations output -json | jq 'with_entries(select(.key | IN("feature_project_id", "feature_project_number", "production_project_id", "production_project_number", "dns_zone_name"))) | map_values(.value)'

inspect-cloud-dns:
	@set -euo pipefail
	project=$$(jq -er '.cloud_values.operations_project_id | select(length > 0)' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email | select(length > 0)' project.json)
	zone=$$(jq -er '.slug' project.json)
	gcloud dns managed-zones describe "$$zone" --project="$$project" --account="$$engineer" --format='json(dnsName,nameServers)' --quiet

inspect-cloud-projects:
	@set -euo pipefail
	folder=$$(jq -er '.cloud_values.folder_id | select(length > 0)' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email | select(length > 0)' project.json)
	gcloud projects list --account="$$engineer" --filter="parent.type=folder AND parent.id=$$folder" --format='json(projectId,projectNumber,lifecycleState,parent)' --quiet

inspect-clerk:
	@python3 infrastructure/cli/provider/helpers/inspect_clerk.py

inspect-vercel:
	@python3 infrastructure/cli/provider/helpers/inspect_vercel.py

inspect-demo-prerequisites-report:
	@set -euo pipefail
	domain=$$(jq -er '.domain' project.json)
	project=$$(jq -er '.cloud_values.operations_project_id' project.json)
	region=$$(jq -er '.cloud_values.region' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email' project.json)
	dig NS "$$domain" +noall +answer +authority
	gcloud artifacts docker images list "$$region-docker.pkg.dev/$$project/public-images" --account="$$engineer" --include-tags --format='json(package,tags)' --quiet

inspect-cache-image-sources:
	@set -euo pipefail
	manifest_config=$$(mktemp -d)
	trap 'rm -rf "$$manifest_config"' EXIT
	while IFS= read -r image; do
		docker --config "$$manifest_config" manifest inspect "$$image"
	done < <(jq -er '.[] | .source + "@" + .digest' infrastructure/terraform/modules/compute-engine-redis/cache-images.json)

inspect-container-engine:
	@docker version --format '{{.Server.Version}}'

publish-cache-images:
	@set -euo pipefail
	project=$$(jq -er '.cloud_values.operations_project_id | select(length > 0)' project.json)
	region=$$(jq -er '.cloud_values.region | select(length > 0)' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email | select(length > 0)' project.json)
	registry="$$region-docker.pkg.dev"
	docker_host=$$(docker context inspect --format '{{.Endpoints.docker.Host}}')
	export DOCKER_CONFIG=$$(mktemp -d)
	trap 'rm -rf "$$DOCKER_CONFIG"' EXIT
	export CLOUDSDK_CORE_ACCOUNT="$$engineer"
	gcloud auth configure-docker "$$registry" --quiet
	while IFS='|' read -r source_image destination_tag platform; do
		destination_image="$$registry/$$project/public-images/$$destination_tag"
		docker --host "$$docker_host" pull --platform "$$platform" "$$source_image"
		docker --host "$$docker_host" tag "$$source_image" "$$destination_image"
		docker --host "$$docker_host" push "$$destination_image"
	done < <(jq -er '.[] | (.source + "@" + .digest) + "|" + (.name + ":" + .version) + "|" + .platform' infrastructure/terraform/modules/compute-engine-redis/cache-images.json)

verify-demo-endpoints:
	@set -euo pipefail
	domain=$$(jq -er '.domain' project.json)
	api="https://demoapi.$$domain/rest/notes"
	curl --fail --silent --show-error --connect-timeout 5 --max-time 30 "$$api/health" > /dev/null
	echo "PASS notes health"
	curl --fail --silent --show-error --connect-timeout 5 --max-time 30 "$$api/openapi" | jq -e '.paths["/rest/notes/notes"].get and .paths["/rest/notes/notes"].post' > /dev/null
	echo "PASS notes GET and POST routes are published"
	status=$$(curl --silent --show-error --connect-timeout 5 --max-time 30 --output /dev/null --write-out '%{http_code}' "$$api/notes")
	case "$$status" in 401|403) echo "PASS unauthenticated notes request rejected with HTTP $$status" ;; *) echo "BLOCKED unauthenticated notes request returned HTTP $$status"; exit 1 ;; esac
	curl --fail --silent --show-error --connect-timeout 5 --max-time 30 "https://demoapp.$$domain" > /dev/null
	echo "PASS demo web page is reachable"

inspect-demo-build:
	@set -euo pipefail
	project=$$(jq -er '.cloud_values.feature_project_id' project.json)
	region=$$(jq -er '.cloud_values.region' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email' project.json)
	gcloud builds list --project="$$project" --region="$$region" --account="$$engineer" --limit=1 --format='json(id,status,createTime,finishTime)' --quiet

inspect-demo-serving:
	@set -euo pipefail
	domain=$$(jq -er '.domain' project.json)
	project=$$(jq -er '.cloud_values.feature_project_id' project.json)
	region=$$(jq -er '.cloud_values.region' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email' project.json)
	curl --silent --show-error --connect-timeout 5 --max-time 20 --output /dev/null --write-out 'Public API HTTP %{http_code}\n' "https://demoapi.$$domain/rest/notes/health" || true
	gcloud run services describe demonotes-s-rest --project="$$project" --region="$$region" --account="$$engineer" --format='json(status.url,status.conditions,status.latestReadyRevisionName)' --quiet
	gcloud certificate-manager certificates describe demossl-certificate --project="$$project" --location=global --account="$$engineer" --format='json(managed)' --quiet
	gcloud certificate-manager maps entries describe democertificate-map-entry --map=democertificate-map --project="$$project" --location=global --account="$$engineer" --format='json(hostname,state,certificates)' --quiet
	gcloud compute target-https-proxies describe demoapi-target-https-proxy --global --project="$$project" --account="$$engineer" --format='json(certificateMap,urlMap)' --quiet
	gcloud compute forwarding-rules describe demoapi-forwarding-rule --global --project="$$project" --account="$$engineer" --format='json(IPAddress,portRange,target)' --quiet
	dig +short "demoapi.$$domain"
	service_url=$$(gcloud run services describe demonotes-s-rest --project="$$project" --region="$$region" --account="$$engineer" --format='value(status.url)' --quiet)
	curl --silent --show-error --connect-timeout 5 --max-time 20 --output /dev/null --write-out 'Direct service health HTTP %{http_code}\n' "$$service_url/rest/notes/health"
	curl --silent --show-error --connect-timeout 5 --max-time 20 --output /dev/null --write-out 'Demo web HTTP %{http_code}\n' "https://demoapp.$$domain"

inspect-demo-summary-errors:
	@set -euo pipefail
	project=$$(jq -er '.cloud_values.feature_project_id' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email' project.json)
	gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name=~"^demonotes-p-" AND NOT httpRequest.requestUrl:"/health"' --project="$$project" --account="$$engineer" --freshness=1h --limit=100 --format='json(timestamp,severity,resource.labels.service_name,httpRequest.status)' --quiet

inspect-demo-summary-queue:
	@set -euo pipefail
	project=$$(jq -er '.cloud_values.feature_project_id' project.json)
	region=$$(jq -er '.cloud_values.region' project.json)
	engineer=$$(jq -er '.cloud_values.engineer_email' project.json)
	queue=$$(gcloud tasks queues list --project="$$project" --location="$$region" --account="$$engineer" --filter='name~demonotes-summarize-note-' --format='value(name)' --quiet)
	queue=$${queue##*/}
	test -n "$$queue"
	gcloud tasks list --project="$$project" --location="$$region" --account="$$engineer" --queue="$$queue" --limit=10 --format='json(name,scheduleTime,dispatchCount,responseCount,lastAttempt.responseStatus,httpRequest.url,httpRequest.oidcToken.audience)' --quiet

demo-note:
	@uv run --project library/providers/gcp python infrastructure/cli/provider/helpers/demo_note.py $(ARGS)

inspect-demo-prerequisites:
	@python3 infrastructure/cli/provider/helpers/doctor.py --stage prerequisites --text

test-onboarding:
	@PYTHONPATH="$(CURDIR):$(CURDIR)/infrastructure/cli/provider/helpers:$$PYTHONPATH" uv run --project library/providers/gcp python -m pytest infrastructure/cli/provider/tests $(ARGS)

inspect-project-routing:
	@python3 infrastructure/cli/provider/helpers/doctor.py --stage local --text
