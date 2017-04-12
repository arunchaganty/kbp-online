LATEX = pdflatex --shell-escape
#LATEX = pdflatex -interaction=nonstopmode
FIGURES = $(wildcard *.tikz)
DOTS = $(wildcard *.dot)
PY = $(wildcard *.py)
PDFS = $(patsubst %.tikz,%.pdf,$(FIGURES))
DOT_PDFS = $(patsubst %.dot,%.pdf,$(DOTS))
PY_PDFS = $(patsubst %.py,%.pdf,$(PY))

all: $(PDFS) $(DOT_PDFS) #$(PY_PDFS)

%.pdf: %.tikz
	$(LATEX) $<

#mention-histogram.pdf:  data/mention-histogram.tsv
#	python mention-histogram.py --input $^ --output $@

clean:
	rm -rf *.{aux,bbl,blg,log,out}
	rm -rf $(OUTPUT).pdf

.PHONY: clean bib final
