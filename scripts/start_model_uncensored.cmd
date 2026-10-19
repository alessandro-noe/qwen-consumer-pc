@echo off
rem Starts Qwen3.8-Flash-Next 125B (full, UNCENSORED/abliterated, ~35 tok/s) on port 8090.
rem Normal (non-abliterated, ~39 tok/s) version: start_model_normal.cmd
rem Fastest measured configuration (RTX 4080 SUPER 16 GB + 32 GB RAM):
rem   n-gram table stays on disk and is read lazily (-lm mmap -lzm on), 64k context, batch 2048
rem   (prompt reading ~860 tok/s warm, generation ~35-40 tok/s).
rem Close this window to free VRAM and RAM.
rem You usually do not need this script: proxy\smistatore.py starts and stops the model on demand.
rem CUDA runtime: the llama.cpp CUDA release ships cudart; if you installed the CUDA Toolkit instead, CUDA_PATH is used.
if defined CUDA_PATH set "PATH=%CUDA_PATH%\bin;%CUDA_PATH%\bin\x64;%PATH%"
"%~dp0..\llama\llama-server.exe" ^
  -m "%~dp0..\models\flashnext_q2_0_abl\Q2_0\Qwen3.8-Flash-Next-GSQ-RCO-abliterated-Q2_0-00001-of-00002.gguf" ^
  -lm mmap -lzm on --port 8090 -c 65536 -np 1 -b 2048 -ub 2048
