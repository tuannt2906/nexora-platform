{{/* Resource name prefix, max 40 chars so suffixes stay within the 63 char DNS limit. */}}
{{- define "nexora.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/* Common labels. Call with (dict "root" . "component" "web"). */}}
{{- define "nexora.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .root.Chart.Name .root.Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/part-of: nexora
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/version: {{ .root.Chart.AppVersion | quote }}
{{- end -}}

{{- define "nexora.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
{{- end -}}

{{/* Immutable image tag; refuses empty and the floating tag "latest". */}}
{{- define "nexora.tag" -}}
{{- $tag := required "image.tag is required: pass an immutable release tag (the git SHA)" .Values.image.tag -}}
{{- if eq $tag "latest" -}}
{{- fail "image.tag must be an immutable tag, never latest" -}}
{{- end -}}
{{- $tag -}}
{{- end -}}

{{/* Full image reference. Call with (list . "control-plane"). */}}
{{- define "nexora.image" -}}
{{- $root := index . 0 -}}
{{- $name := index . 1 -}}
{{- printf "%s/%s:%s" (required "image.registry is required, e.g. ghcr.io/<owner>/nexora-platform" $root.Values.image.registry) $name (include "nexora.tag" $root) -}}
{{- end -}}

{{- define "nexora.pullSecrets" -}}
{{- with .Values.image.pullSecrets }}
imagePullSecrets:
{{- range . }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end -}}
