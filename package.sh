#!/usr/bin/env bash
# Packages this beacon code into a cute little zip file :)

./tools/clean.sh

wget https://raw.githubusercontent.com/adafruit/Adafruit_CircuitPython_IRRemote/main/adafruit_irremote.py -O ./lib/adafruit_irremote.py

git submodule update --remote

zip -r beacon-code.zip . -x .gitignore -x .gitmodules -x .git -x servercom -x tools/\* -x .git/\* -x lib/.git/\* -x servercom/\* -x package.sh # 2>&1 > /dev/null
echo beacon-code.zip
