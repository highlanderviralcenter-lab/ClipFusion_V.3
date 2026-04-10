#!/usr/bin/env bash
set -euo pipefail

# Alguns ambientes não incluem /sbin no PATH de shells não-login.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

echo "Kernel cmdline:"
cat /proc/cmdline

echo "VAAPI:"
if command -v vainfo >/dev/null 2>&1; then
  vainfo | head -n 5
else
  echo "vainfo não instalado"
fi

echo "Swaps:"
if command -v swapon >/dev/null 2>&1; then
  swapon --show
else
  echo "swapon não encontrado no PATH"
fi

echo "Swappiness:"
if command -v sysctl >/dev/null 2>&1; then
  sysctl -n vm.swappiness
else
  echo "sysctl não encontrado no PATH"
fi
