#!/usr/bin/env bash
# rollback.sh — Automated Deployment Rollback
set -euo pipefail

echo "[ ROLLBACK ] Initiating emergency rollback for Alluci Sovereign Agent..."

# Target deployment and namespace
DEPLOYMENT="alluci-backend"
NAMESPACE="alluci"

# 1. Trigger the undo
echo "[ ROLLBACK ] Reverting to the previous successful revision..."
if command -v kubectl >/dev/null 2>&1; then
  kubectl rollout undo deployment/$DEPLOYMENT -n $NAMESPACE
  
  # 2. Wait for completion
  echo "[ ROLLBACK ] Monitoring rollout status..."
  kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE
  
  echo "[ ROLLBACK ] SUCCESS: System has been restored to the previous state."
else
  echo "[ SKIPPED ] 'kubectl' not found. In a real environment, this would execute the cluster rollback."
  echo "[ INFO ] Manual intervention required if deployment is failing."
fi
