for f in data/pooling_bias_closed-world.tsv data/pooling_bias_condensed.tsv data/pooling_bias_anydoc.tsv data/pooling_bias_condensed-anydoc.tsv; do
    o=`basename $f .tsv`.pdf
    echo "Plotting $f to $o";
    python render_pooling_bias.py -i $f -o pooling_bias/$o -m "macro_f1";
done;
