%.pdf: %.dot
	dot $< -Tpdf > $@