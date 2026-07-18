#!/usr/bin/env bash
set -Eeuo pipefail
DIR="${BSI_SMT_DIR:-$HOME/BSI_SMT}"
cd "$HOME"
if [[ -d "$DIR/.git" ]];then git -C "$DIR" fetch origin main;git -C "$DIR" reset --hard origin/main
else git clone https://github.com/efife1/BSI_SMT.git "$DIR";fi
exec bash "$DIR/installer/install.sh"
