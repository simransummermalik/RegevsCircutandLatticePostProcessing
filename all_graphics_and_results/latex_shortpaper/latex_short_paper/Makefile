.PHONY: all verify clean

all: main.pdf

main.pdf: main.tex references.bib figures/certification_vs_recovery.png
	tectonic main.tex

latexmk:
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

verify:
	python3 verify_data.py

clean:
	tectonic -c minimal main.tex
