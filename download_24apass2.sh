#!/bin/sh

python $TPCQCVIS_DIR/TPCQCVis/tools/downloadFromAlien.py $TPCQCVIS_DATA/2024/LHC24ar/apass2_old_alignment_realistic/ /alice/data/2024/LHC24ar/ apass2_old_alignment_realistic 559827
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadFromAlien.py $TPCQCVIS_DATA/2024/LHC24ar/apass2_old_alignment2_realistic/ /alice/data/2024/LHC24ar/ apass2_old_alignment2_realistic 559827
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadFromAlien.py $TPCQCVIS_DATA/2024/LHC24ar/apass2_new_alignment_realistic/ /alice/data/2024/LHC24ar/ apass2_new_alignment_realistic 559827
python $TPCQCVIS_DIR/TPCQCVis/tools/downloadFromAlien.py $TPCQCVIS_DATA/2024/LHC24ar/apass2_new_alignment2_realistic/ /alice/data/2024/LHC24ar/ apass2_new_alignment2_realistic 559827

echo " DONE WITH DOWNLOADING "

cp $TPCQCVIS_DATA/2024/LHC24ar/apass2_old_alignment_realistic/559827.root $TPCQCVIS_DATA/2024/LHC24ar/apass2_alignementComp/100001.root
cp $TPCQCVIS_DATA/2024/LHC24ar/apass2_old_alignment2_realistic/559827.root $TPCQCVIS_DATA/2024/LHC24ar/apass2_alignementComp/200002.root
cp $TPCQCVIS_DATA/2024/LHC24ar/apass2_new_alignment_realistic/559827.root $TPCQCVIS_DATA/2024/LHC24ar/apass2_alignementComp/300003.root
cp $TPCQCVIS_DATA/2024/LHC24ar/apass2_new_alignment2_realistic/559827.root $TPCQCVIS_DATA/2024/LHC24ar/apass2_alignementComp/400004.root

echo "DONE WITH COPYING "

