@echo off
rem Starts the proxy (smistatore) on port 8091. Point OpenCode or any OpenAI-compatible client at http://127.0.0.1:8091/v1
rem The proxy starts the model on the first request and stops it after 30 idle minutes.
rem SMISTA_SCALATA=1: the model works with thinking OFF and turns it ON after 2 real tool failures
rem   (5 hard tasks: 5/5 in 19-36 min, mean ~28, instead of 68 with thinking always on).
rem SMISTA_NOTE=0: no routing notes (they need the optional Kev-4B decision model).
rem Do not keep Kev-4B running with 32 GB RAM: it steals page cache and makes prompt reading 2-3x slower (measured).
cd /d %~dp0..
set SMISTA_SCALATA=1
set SMISTA_NOTE=0
start "smistatore" /min python proxy\smistatore.py
