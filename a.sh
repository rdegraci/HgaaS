#!/usr/bin/bash
#while sleep 1; do
for i in `seq 1 30`; do sleep 1;
	echo -n "a | $1 | $i |  "
	date
done | tee -a asdf_a.log
