#!/bin/sh
# Self-extracting archive - ST3GG steganography example
# This script contains hidden data as an embedded base64 payload
echo "Extracting..."
PAYLOAD="H4sIADoKymkC/+3NMQoCQQyF4RzFC4wzwjJ7AgtB1EoQphHZC+yOYGm9ndZWFmurV8pJDLJYaO02/h+EF5JAmmpXV3mcD1l+JphYFK80nxkm4b3r52UZo4yCDGDf5G1tL+U/aXvX49VZ6eXWd067k5+npV+nqU8ra2d+kTZeu7P7Otb2IQAAAAAAAAAAAAAAAACAwT0BI/+JWAAoAAA="
echo "$PAYLOAD" | base64 -d | tar xzf - 2>/dev/null
if [ -f secret.txt ]; then
    echo "Secret extracted to secret.txt"
    cat secret.txt
else
    echo "Extraction failed"
fi
# Hidden direct payload (not used by extraction):
# 4oqw4oCiLeKAouKcp+KAoi3igKIt4qaRL0xcTy9WXEUvXFAvTFxJL05cWS/ippIt4oCiLeKAouKcp+KAoi3igKLiirE=
# End of self-extracting archive
