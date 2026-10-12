# SPDX-License-Identifier: GPL-2.0-or-later
set -x
cd /sl
export PATH=/sl/.node22/bin:$PATH HOME=/tmp npm_config_cache=/tmp/npm
bash bench/run.sh traces/axis_stock_2655e62fe_100ms.jsonl.gz && cp bench/results/env.txt bench/results/env_cnc.txt
bash bench/run.sh traces/axis_100ms.jsonl.gz
REPEATS_CPP=5 REPEATS_PY=2 REPEATS_NODE=10 bash bench/run.sh traces/axis_stock_2655e62fe_20ms.jsonl.gz
REPEATS_CPP=5 REPEATS_PY=2 REPEATS_NODE=10 bash bench/run.sh traces/axis_20ms.jsonl.gz
echo ALLDONE
