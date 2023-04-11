#!/usr/bin/env bash
# A utility for cleaning things up before releases and such

rm ./lib/adafruit_irremote.py || echo no irremote installed so none to remove.
rm ./beacon-code.zip || echo no zip generated so none to remove

git submodule update --init --recursive
