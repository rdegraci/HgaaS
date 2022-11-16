#while sleep 1; do
for i in `seq 1 30`; do 
    sleep 0.1
	bash ./modules/poop.sh
	date
done
