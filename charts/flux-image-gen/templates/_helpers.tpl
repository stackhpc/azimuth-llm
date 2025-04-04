{{/*
Expand the name of the chart.
*/}}
{{- define "flux-image-gen.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "flux-image-gen.fullname" -}}
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
{{- define "flux-image-gen.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "flux-image-gen.labels" -}}
helm.sh/chart: {{ include "flux-image-gen.chart" . }}
{{ include "flux-image-gen.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "flux-image-gen.selectorLabels" -}}
app.kubernetes.io/name: {{ include "flux-image-gen.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Model selector labels
*/}}
{{- define "flux-image-gen.modelLabels" -}}
app.kubernetes.io/component: {{ . }}-api
{{- end }}

{{/*
UI selector labels
*/}}
{{- define "flux-image-gen.uiLabels" -}}
app.kubernetes.io/component: {{ .Release.Name }}-ui
{{- end }}


{{/*
Create the name of the service account to use
*/}}
{{- define "flux-image-gen.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "flux-image-gen.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
