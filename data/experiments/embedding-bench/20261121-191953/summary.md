# Embedding benchmark

Run folder: `data/experiments/embedding-bench/20261121-191953`  
Machine: 12th Gen Intel(R) Core(TM) i7-12700H, 20 logical CPUs, 23.6 GB RAM; low-end profile pinned to E-cores [12, 13, 14, 15]  
Harness self-check (recorded 20260928-eval-A-full-491f137 re-scored = saved summary): **True**

## Retrieval quality (32 answerable eval questions; 16 EN, 16 VI; raw cosine top-k, arm A)

| Model | Section@1 | @3 | @5 | @10 | Source@5 | MRR@10 | EN @1 / @5 | VI @1 / @5 | vs Gemini @5 (win/loss) |
|---|---|---|---|---|---|---|---|---|---|
| gemini | 26/32 | 29 | 30 | 32 | 31 | 1.000 | 13 / 16 | 13 / 14 |  |
| gemma1-fp32 | 24/32 | 27 | 29 | 30 | 29 | 0.961 | 13 / 15 | 11 / 14 | 1/2 |
| gemma1-fp16 | 24/32 | 27 | 29 | 30 | 29 | 0.961 | 13 / 15 | 11 / 14 | 1/2 |
| gemma1-int8 | 24/32 | 27 | 29 | 30 | 29 | 0.959 | 13 / 15 | 11 / 14 | 1/2 |
| gemma1-int4 | 23/32 | 26 | 29 | 30 | 29 | 0.939 | 13 / 15 | 10 / 14 | 1/2 |
| gemma2-fp32 | 20/32 | 25 | 28 | 29 | 30 | 0.867 | 12 / 15 | 8 / 13 | 2/4 |
| gemma2-fp16 | 20/32 | 25 | 28 | 29 | 30 | 0.867 | 12 / 15 | 8 / 13 | 2/4 |
| gemma2-int8 | 20/32 | 25 | 28 | 29 | 30 | 0.867 | 12 / 15 | 8 / 13 | 2/4 |
| gemma2-int4 | 20/32 | 26 | 28 | 31 | 30 | 0.870 | 12 / 14 | 8 / 14 | 2/4 |

## Speed and memory

| Model | Profile | Load s | Index docs/s | Index tokens/s | Query p50 ms | Query p90 ms | Peak RAM MB | Peak private MB | Truncated chunks |
|---|---|---|---|---|---|---|---|---|---|
| gemma1-fp32 | full | 1.4 | 10.7 | 2507 | 29 | 37 | 977 | 1776 | 0/733 |
| gemma1-fp32 | lowend | 2.0 | 2.3 | 526 | 106 | 146 | 933 | 1703 | 0/200 |
| gemma1-fp16 | full | 1.7 | 9.7 | 2280 | 33 | 41 | 1024 | 1785 | 0/733 |
| gemma1-fp16 | lowend | 2.8 | 2.1 | 492 | 113 | 167 | 959 | 1705 | 0/200 |
| gemma1-int8 | full | 1.0 | 8.7 | 2030 | 124 | 133 | 1648 | 1967 | 0/733 |
| gemma1-int8 | lowend | 1.6 | 2.1 | 485 | 245 | 285 | 1643 | 2948 | 0/200 |
| gemma1-int4 | full | 1.1 | 4.8 | 1114 | 52 | 76 | 553 | 1184 | 0/733 |
| gemma1-int4 | lowend | 1.7 | 1.4 | 327 | 165 | 234 | 502 | 1108 | 0/200 |
| gemma2-fp32 | full | 1.3 | 6.8 | 1587 | 41 | 49 | 1736 | 3417 | 0/733 |
| gemma2-fp32 | lowend | 2.0 | 1.6 | 368 | 152 | 212 | 1723 | 3381 | 0/200 |
| gemma2-fp16 | full | 2.0 | 5.0 | 1174 | 50 | 61 | 1788 | 3429 | 0/733 |
| gemma2-fp16 | lowend | 2.9 | 1.4 | 324 | 159 | 226 | 1885 | 3397 | 0/200 |
| gemma2-int8 | full | 0.9 | 5.3 | 1242 | 204 | 218 | 1377 | 2914 | 0/733 |
| gemma2-int8 | lowend | 1.4 | 1.4 | 328 | 497 | 589 | 1375 | 2883 | 0/200 |
| gemma2-int4 | full | 1.0 | 7.0 | 1632 | 36 | 45 | 1289 | 2965 | 0/733 |
| gemma2-int4 | lowend | 1.5 | 1.5 | 352 | 178 | 239 | 1281 | 2925 | 0/200 |

## Precision fidelity (against the same model's FP32)

| Model | Doc cosine mean | Doc cosine min | Query top-5 overlap |
|---|---|---|---|
| gemma1-fp16 | 1.0000 | 1.0000 | 0.99 |
| gemma1-int8 | 0.9893 | 0.9802 | 0.92 |
| gemma1-int4 | 0.9593 | 0.9358 | 0.88 |
| gemma2-fp16 | 1.0000 | 1.0000 | 1.00 |
| gemma2-int8 | 0.9999 | 0.9999 | 0.99 |
| gemma2-int4 | 0.9829 | 0.9764 | 0.87 |

Vectors with NaN/Inf or zero norm: none
