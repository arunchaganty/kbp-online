KBS=(kb_alternate_names_2016_8_28_16 kb_patterns_2016_8_28_16 kb_rnn_unk_2016_8_28_16 kb_supervised_2016_8_28_16 kb_website_2016_8_28_16)
KBS_=(kb_patterns_all_2016_8_28_16 kb_rnn_unk_2016_8_28_16 kb_supervised_2016_8_28_16)

#for kb in ${KBS[@]}; do
#  echo $kb
#  python3 scripts/prepare_pooled_data.py submission -k "$kb" -o data/_$kb.tsv
#  python3 scripts/clean.py -i data/_$kb.tsv -o data/$kb.tsv
#done;
#cat data/kb_alternate_names_2016_8_28_16.tsv data/kb_patterns_2016_8_28_16.tsv data/kb_website_2016_8_28_16.tsv | sort -u > data/kb_patterns_all_2016_8_28_16.tsv;

OLD_ENTRIES=
for kb in ${KBS_[@]}; do
  echo $kb;
  python3 scripts/prepare_pooled_data.py sample -i data/$kb.tsv -o data/pooled-$kb.tsv -n 2000 $OLD_ENTRIES;
  OLD_ENTRIES="$OLD_ENTRIES data/pooled-$kb.tsv"
done;

for kb in ${KBS_[@]}; do
  echo $kb;
  python3 scripts/prepare_pooled_data.py make -i data/pooled-$kb.tsv -o data/pooled-$kb/;
done;
