{{/*
Chart name. Hardcoded rather than derived from .Chart.Name so labels stay
stable when this chart is pulled in as an aliased subchart.
*/}}
{{- define "azimuth-omni-backend.name" -}}
{{- default "azimuth-llm-omni-backend" .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Chart label.
*/}}
{{- define "azimuth-omni-backend.chart" -}}
{{- printf "%s-%s" (include "azimuth-omni-backend.name" .) .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}
