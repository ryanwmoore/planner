%.pdf: %.dot
	dot $< -Tpdf > $@

%.png: %.dot
	dot $< -Tpng > $@
