all: README.md

README.md: README.md.in
	awk -f includefiles.awk $< >$@ || rm -f $@

README.html: README.md
	pandoc --standalone --self-contained --css pandoc.css  -o $@ $<

clean:
	rm -f README.md
