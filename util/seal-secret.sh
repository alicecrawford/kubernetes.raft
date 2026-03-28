#!/usr/bin/env bash

namespace=$1
name=$2

if [ "${name}" == "" ]; then
  kubectl -n ${namespace} get secrets
  exit 0
fi

if [ ! -d secrets ]; then
  mkdir secrets
fi

kubectl -n ${namespace} -o yaml get secret ${name} > secrets/${name}-secret.yaml
kubeseal --controller-name sealed-secrets -f secrets/${name}-secret.yaml -w ${name}-sealedsecret.yaml
