{{/*
Expand the name of the chart.
*/}}
{{- define "azimuth-llm.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "azimuth-llm.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "azimuth-llm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "azimuth-llm.labels" -}}
helm.sh/chart: {{ include "azimuth-llm.chart" . }}
{{ include "azimuth-llm.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
App selector labels
*/}}
{{- define "azimuth-llm.selectorLabels" -}}
app.kubernetes.io/name: {{ include "azimuth-llm.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API component selector labels
*/}}
{{- define "azimuth-llm.api-selectorLabels" -}}
{{ include "azimuth-llm.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
UI component selector labels
*/}}
{{- define "azimuth-llm.ui-selectorLabels" -}}
{{ include "azimuth-llm.selectorLabels" . }}
app.kubernetes.io/component: ui
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "azimuth-llm.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "azimuth-llm.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Workaround for models which don't yet contain chat templates in their HuggingFace repos.
If a chat template is provided in the Helm values then this is used, otherwise we omit the
chat template for all models apart from a list of known cases where the upstream repo is
not responsive to adding a chat template to their repo.
*/}}
{{- define "azimuth-llm.chatTemplate" -}}
{{- if .Values.huggingface.chatTemplate }}
- --chat-template
- {{ quote .Values.huggingface.chatTemplate }}
{{- else if contains "WizardCoder" .Values.huggingface.model }}
- --chat-template
- {{ quote "{% for message in messages %}{% if message['role'] == 'system' %}{% endif %}{% if message['role'] == 'user' %}{{ '### Instruction:\n' }}{% endif %}{% if message['role'] == 'assistant' %}{{ '### Response:\n' }}{% endif %}{{ message['content'].strip() }}{% if not loop.last %}{{ '\n\n' }}{% endif %}{% if message['role'] == 'user' and loop.last %}{{ '### Response:\n' }}{% endif %}{% endfor %}" }}
{{- end -}}
{{- end }}