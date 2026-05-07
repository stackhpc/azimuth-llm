{{/*
Render a full vLLM backend (Deployment + Service + optional
ingress/httproute/zenith/pdb/servicemonitor) for one modality.

Usage:
  {{- include "azimuth-omni-backend.backend" (dict "root" . "alias" "ttt") }}

Per-modality config is read from `.Values.<alias>`.
*/}}

{{/*
Selector labels, distinct per alias so deployments don't select each
other's pods.
*/}}
{{- define "azimuth-omni-backend.backend-selectorLabels" -}}
{{- $alias := .alias -}}
{{- $root := .root -}}
app.kubernetes.io/name: {{ include "azimuth-omni-backend.name" $root }}
app.kubernetes.io/instance: {{ $root.Release.Name }}
app.kubernetes.io/component: backend
azimuth-omni.stackhpc.com/modality: {{ $alias }}
{{- end }}

{{/*
Common labels for a backend resource.
*/}}
{{- define "azimuth-omni-backend.backend-labels" -}}
helm.sh/chart: {{ include "azimuth-omni-backend.chart" .root }}
{{ include "azimuth-omni-backend.backend-selectorLabels" . }}
{{- if .root.Chart.AppVersion }}
app.kubernetes.io/version: {{ .root.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
{{- end }}

{{/*
Conditional chat-template arg.
*/}}
{{- define "azimuth-omni-backend.chatTemplate" -}}
{{- $cfg := .cfg -}}
{{- if $cfg.chatTemplate }}
- --chat-template
- {{ quote $cfg.chatTemplate }}
{{- else if contains "WizardCoder" $cfg.huggingface.model }}
- --chat-template
- {{ quote "{% for message in messages %}{% if message['role'] == 'system' %}{% endif %}{% if message['role'] == 'user' %}{{ '### Instruction:\n' }}{% endif %}{% if message['role'] == 'assistant' %}{{ '### Response:\n' }}{% endif %}{{ message['content'].strip() }}{% if not loop.last %}{{ '\n\n' }}{% endif %}{% if message['role'] == 'user' and loop.last %}{{ '### Response:\n' }}{% endif %}{% endfor %}" }}
{{- end -}}
{{- end }}

{{/*
Renders every resource for one modality.
*/}}
{{- define "azimuth-omni-backend.backend" -}}
{{- $root := .root -}}
{{- $alias := .alias -}}
{{- $cfg := index $root.Values $alias -}}
{{- if not $cfg }}{{- fail (printf "azimuth-omni-backend: missing values block for backend %q" $alias) }}{{- end }}
{{- if not $cfg.enabled -}}

{{- else -}}
{{- $name := printf "%s-%s" $root.Release.Name $alias -}}
{{- $labelArgs := dict "root" $root "alias" $alias -}}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}
  labels:
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
spec:
  replicas: {{ default 1 $cfg.api.replicas }}
  selector:
    matchLabels:
      {{- include "azimuth-omni-backend.backend-selectorLabels" $labelArgs | nindent 6 }}
  strategy:
    {{- $cfg.api.updateStrategy | toYaml | nindent 4 }}
  template:
    metadata:
      labels:
        {{- include "azimuth-omni-backend.backend-selectorLabels" $labelArgs | nindent 8 }}
    spec:
      containers:
      - name: api
        image: "{{ $cfg.api.image.containerImage }}:{{ $cfg.api.image.version }}"
        command:
        - vllm
        - serve
        ports:
        - name: api
          containerPort: 8000
        volumeMounts:
        - name: data
          mountPath: /root/.cache/huggingface
        - name: shm
          mountPath: /dev/shm
        args:
          - --omni
          {{- if semverCompare "<v0.13.0" $cfg.api.image.version }}
          - --model
          {{- end }}
          - {{ $cfg.huggingface.model }}
          {{- include "azimuth-omni-backend.chatTemplate" (dict "cfg" $cfg) | nindent 10 -}}
          {{- if $cfg.api.modelMaxContextLength }}
          - --max-model-len
          - {{ $cfg.api.modelMaxContextLength | quote }}
          {{- end }}
          {{- if and (not (has "--tokenizer-mode" $cfg.api.extraArgs)) (hasPrefix "mistralai/" $cfg.huggingface.model) }}
          - --tokenizer-mode
          - mistral
          {{- end }}
          {{- with $cfg.api.extraArgs }}
          {{- toYaml . | nindent 10 }}
          {{- end }}
        {{- if $cfg.huggingface.secretName }}
        envFrom:
        - secretRef:
            name: {{ $cfg.huggingface.secretName }}
        {{- end }}
        env:
        - name: DO_NOT_TRACK
          value: "1"
        {{- with $cfg.api.extraEnv }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
        {{- if $cfg.huggingface.token }}
        - name: HUGGING_FACE_HUB_TOKEN
          value: {{ quote $cfg.huggingface.token }}
        {{- end }}
        readinessProbe:
          httpGet:
            port: 8000
            path: /health
          periodSeconds: 10
        resources:
          limits:
            nvidia.com/gpu: {{ $cfg.api.gpus | int }}
      volumes:
        - name: data
          {{- $cfg.api.cacheVolume | toYaml | nindent 10 }}
        - name: shm
          emptyDir:
            medium: Memory
            sizeLimit: 1Gi
      {{- with $cfg.api }}
      {{- if .azimuthNodeGroupSelector }}
      nodeSelector:
        capi.stackhpc.com/node-group: {{ .azimuthNodeGroupSelector | quote }}
      {{- else if .nodeSelector }}
      nodeSelector:
        {{- toYaml .nodeSelector | nindent 8 }}
      {{- end }}
      {{- end }}
      {{- with $cfg.api.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with $cfg.api.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}
  labels:
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
spec:
  ports:
  - name: api
    port: 80
    protocol: TCP
    targetPort: api
  type: {{ $cfg.api.service.type }}
  selector:
    {{- include "azimuth-omni-backend.backend-selectorLabels" $labelArgs | nindent 4 }}
{{- if and $cfg.api.monitoring $cfg.api.monitoring.enabled }}
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ $name }}
  labels:
    app: {{ $name }}
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
spec:
  endpoints:
  - port: api
    path: /metrics
  jobLabel: operator
  namespaceSelector:
    matchNames:
    - {{ $root.Release.Namespace }}
  selector:
    matchLabels:
      {{- include "azimuth-omni-backend.backend-selectorLabels" $labelArgs | nindent 6 }}
{{- end }}
{{- if and $cfg.api.service.zenith $cfg.api.service.zenith.enabled }}
---
apiVersion: zenith.stackhpc.com/v1alpha1
kind: Client
metadata:
  name: {{ $name }}
  labels:
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
spec:
  reservationName: {{ $name }}
  upstream:
    serviceName: {{ $name }}
  auth:
    skip: {{ $cfg.api.service.zenith.skipAuth }}
---
apiVersion: zenith.stackhpc.com/v1alpha1
kind: Reservation
metadata:
  name: {{ $name }}
  labels:
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
  annotations:
    azimuth.stackhpc.com/service-label: {{ quote $cfg.api.service.zenith.label }}
    azimuth.stackhpc.com/service-icon-url: {{ $cfg.api.service.zenith.iconUrl }}
    {{- with $cfg.api.service.zenith.description }}
    azimuth.stackhpc.com/service-description: {{ quote . }}
    {{- end }}
spec:
  credentialSecretName: {{ $name }}-zenith-credential
{{- end }}
{{- if $cfg.api.httpRoute.enabled }}
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: {{ $name }}
  labels:
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
  {{- with $cfg.api.httpRoute.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- with $cfg.api.httpRoute.parentRefs }}
  parentRefs:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- with $cfg.api.httpRoute.hostnames }}
  hostnames:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  rules:
    {{- range $cfg.api.httpRoute.rules }}
    - {{ with .matches }}matches:
        {{- toYaml . | nindent 8 }}
      {{ end }}backendRefs:
        - name: {{ $name }}
          port: 80
    {{- end }}
{{- end }}
{{- if $cfg.api.ingress.enabled }}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ $name }}
  labels:
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
  {{- with $cfg.api.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- with $cfg.api.ingress.className }}
  ingressClassName: {{ . }}
  {{- end }}
  {{- if $cfg.api.ingress.tls }}
  tls:
    {{- range $cfg.api.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range $cfg.api.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            {{- with .pathType }}
            pathType: {{ . }}
            {{- end }}
            backend:
              service:
                name: {{ $name }}
                port:
                  number: 80
          {{- end }}
    {{- end }}
{{- end }}
{{- if $cfg.api.pdb.enabled }}
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ $name }}
  labels:
    {{- include "azimuth-omni-backend.backend-labels" $labelArgs | nindent 4 }}
spec:
  {{- with $cfg.api.pdb.minAvailable }}
  minAvailable: {{ . }}
  {{- end }}
  {{- with $cfg.api.pdb.maxUnavailable }}
  maxUnavailable: {{ . }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "azimuth-omni-backend.backend-selectorLabels" $labelArgs | nindent 6 }}
{{- end }}
{{- end }}
{{- end }}
