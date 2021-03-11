# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SPHINXAPIDOC  ?= sphinx-apidoc
SOURCEDIR     = source
BUILDDIR      = build
MODDIR        ?= ../cardano_clusterlib
CARDANO_CLUSTERLIB_GIT_REV  ?= $(shell git rev-parse HEAD)

export CARDANO_CLUSTERLIB_GIT_REV

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

apidoc:
	@$(SPHINXAPIDOC) -f -H "Source Documentation" -o "$(SOURCEDIR)" "$(MODDIR)"

clean:
	rm -rf "$(BUILDDIR)"/*

.PHONY: help apidoc clean Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile apidoc
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
