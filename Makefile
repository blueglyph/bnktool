BANK_FILES = $(shell ls *.bnk)

all: $(BANK_FILES)

%.bnk: %.txt
	python bnktool.py $@ -e [$<]
