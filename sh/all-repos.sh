for D in "$@" 
do
   ./bba.sh ${D} | tee  ${D}.txt  
done
