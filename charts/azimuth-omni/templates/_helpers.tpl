{{/*
Chart name.
*/}}
{{- define "azimuth-omni.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name.
*/}}
{{- define "azimuth-omni.fullname" -}}
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
Chart label.
*/}}
{{- define "azimuth-omni.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "azimuth-omni.labels" -}}
helm.sh/chart: {{ include "azimuth-omni.chart" . }}
{{ include "azimuth-omni.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
App selector labels.
*/}}
{{- define "azimuth-omni.selectorLabels" -}}
app.kubernetes.io/name: {{ include "azimuth-omni.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
UI component selector labels.
*/}}
{{- define "azimuth-omni.ui-selectorLabels" -}}
{{ include "azimuth-omni.selectorLabels" . }}
app.kubernetes.io/component: ui
{{- end }}

