%.pdf: %.dot
	dot $< -Tpdf > $@
