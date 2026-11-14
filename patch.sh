#!/bin/bash
# Binary patches for Wine compat, applied to the runtime copies in $1 (originals untouched).
# Each: file offset, expected bytes, replacement bytes (hex).
p() { f=$1/$2; cur=$(xxd -p -s $3 -l $(( ${#4}/2 )) "$f")
  if [ "$cur" = "$4" ]; then echo "$5" | xxd -r -p | dd of="$f" bs=1 seek=$(($3)) conv=notrunc status=none; echo "patched $2@$3"
  elif [ "$cur" != "$5" ]; then echo "WARN $2@$3: unexpected bytes $cur (different build?)"; fi; }
# AuthServer ODBC init: SQLSetEnvAttr(NULL, CONNECTION_POOLING) crashes Wine's odbc32. call [iat] -> add esp,16 (stdcall args).
p "$1" AuthServer.exe 0xd0e5  ff15fc214600 83c410909090
p "$1" AuthServer.exe 0x109c1 ff15fc214600 83c410909090
