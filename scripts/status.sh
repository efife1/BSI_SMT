#!/usr/bin/env bash
cd "$(dirname "$0")/.."
sudo docker compose ps
curl -fsS http://localhost:8000/ || true
