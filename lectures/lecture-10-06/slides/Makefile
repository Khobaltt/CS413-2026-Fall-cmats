.PHONY: all
all: lambda1_vp.pdf

lambda1_vp.pdf: lambda1_vp.tex
	mkdir -p .build
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build $<
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build $<
	cp .build/lambda1_vp.pdf $@
