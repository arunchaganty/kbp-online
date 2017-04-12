default: refdb-update figures
	pdflatex main
	bibtex main

figures:
	make -C figures

clean:
	rm main.aux main.log main.out main.bbl main.blg

refdb:
	git clone https://github.com/percyliang/refdb

refdb-update: 
	make -C refdb

run:
	go main.pdf

paper.zip:
	zip -R paper.zip figures refdb/all.bib *.tex *.sty *.tables *.sty *.bst *.bbl *.blg Makefile

.PHONY: figures clean refdb refdb-update paper.zip
		
