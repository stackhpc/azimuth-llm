{ pkgs, ... }:
let
  allComponents = "chat image-analysis flux-image-gen";
  imagePrefix = "ghcr.io/stackhpc/azimuth-llm";
  webAppsDir = "./web-apps";

  # Resolves "all" or empty arg to the full list, validates otherwise.
  resolveComponents = ''
    ALL_COMPONENTS="${allComponents}"

    resolve_components() {
      local input="$1"
      if [ -z "$input" ] || [ "$input" = "all" ]; then
        echo "$ALL_COMPONENTS"
      else
        for c in $input; do
          if ! echo " $ALL_COMPONENTS " | grep -q " $c "; then
            echo "Unknown component: $c" >&2
            echo "Available: $ALL_COMPONENTS" >&2
            return 1
          fi
        done
        echo "$input"
      fi
    }

    image_name() {
      echo "${imagePrefix}-''${1}-ui"
    }
  '';
in
{
  env.GREET = "azimuth-llm dev environment";

  packages = with pkgs; [
    git
    # Container
    grype
    # Helm / K8s
    kubernetes-helm
    chart-testing
    kind
    kubectl
    # CI tooling
    jq
    yq-go
    # Python
    python311
    ruff
    black
  ];

  treefmt = {
    enable = true;
    config.programs = {
      nixfmt.enable = true;
      black.enable = true;
    };
  };

  git-hooks.hooks = {
    treefmt = {
      enable = true;
      settings.fail-on-change = false;
    };
  };

  difftastic.enable = true;

  scripts = {
    build.exec = ''
      ${resolveComponents}
      TAG="latest"
      COMPONENT=""
      while [ $# -gt 0 ]; do
        case "$1" in
          --tag) TAG="$2"; shift 2 ;;
          *)     COMPONENT="$COMPONENT $1"; shift ;;
        esac
      done
      COMPONENT="''${COMPONENT## }"

      TARGETS=$(resolve_components "$COMPONENT") || exit 1
      for c in $TARGETS; do
        echo "==> Building $c (tag: $TAG)"
        docker build \
          -t "$(image_name "$c"):$TAG" \
          -f ${webAppsDir}/"$c"/Dockerfile \
          ${webAppsDir}/
      done
    '';

    scan.exec = ''
      ${resolveComponents}
      TAG="latest"
      FAIL_ON="critical"
      COMPONENT=""
      while [ $# -gt 0 ]; do
        case "$1" in
          --tag)     TAG="$2"; shift 2 ;;
          --fail-on) FAIL_ON="$2"; shift 2 ;;
          *)         COMPONENT="$COMPONENT $1"; shift ;;
        esac
      done
      COMPONENT="''${COMPONENT## }"

      TARGETS=$(resolve_components "$COMPONENT") || exit 1
      EXIT=0
      for c in $TARGETS; do
        build "$c" --tag "$TAG"

        IMAGE="$(image_name "$c"):$TAG"
        echo ""
        echo "==> Scanning $IMAGE (fail-on: $FAIL_ON)"
        if ! grype "$IMAGE" --fail-on "$FAIL_ON" --only-fixed; then
          EXIT=1
        fi
      done
      exit $EXIT
    '';
  };

  enterShell = ''
    echo "$GREET"
    echo ""
    echo "Commands (component = chat | image-analysis | flux-image-gen | omit for all):"
    echo ""
    echo "  prek  -a                                       Format/lint all files"
    echo "  build [component] [--tag TAG]                  Build container image(s)"
    echo "  scan  [component] [--tag TAG] [--fail-on SEV]  Build if needed + Grype scan"
    echo ""
  '';
}
