#/***************************************************************************
# ThreeDiToolbox
#
# Toolbox for working with 3Di hydraulic models
#							 -------------------
#		begin				: 2016-03-04
#		git sha				: $Format:%H$
#		copyright			: (C) 2016 by Nelen&Schuurmans
#		email				: servicedesk@nelen-schuurmans.nl
# ***************************************************************************/
#
#/***************************************************************************
# *																		 *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or	 *
# *   (at your option) any later version.								   *
# *																		 *
# ***************************************************************************/

#################################################
# Edit the following to match your sources lists
#################################################


#Add iso code for any locales you want to support here (space separated)
# default is no locales
LOCALES =


# translation
SOURCES = __init__.py threedi_plugin.py

PLUGINNAME = ThreeDiToolbox

PY_FILES = __init__.py
# ^^^ The rest of the python files is picked up because they're in git.

UI_FILES = ui/*.ui

EXTRAS = metadata.txt icon.png

HELP = help/build/html

default: compile

compile: external-dependencies/.generated.marker

# .generated.marker is generated by populate.sh to signify completion.
external-dependencies/.generated.marker: constraints.txt external-dependencies/populate.sh
	cd external-dependencies && ./populate.sh

constraints.txt: dependencies.py
	python3 dependencies.py

test: compile
	@echo "#### Python tests"
	QT_QPA_PLATFORM=offscreen pytest --cov --ignore ./deps

docstrings:
	@echo "#### Docstring coverage report"
	python3 scripts/docstring-report.py

zip: compile
	@echo
	@echo "---------------------------"
	@echo "Creating plugin zip bundle."
	@echo "---------------------------"
	rm -rf /tmp/$(PLUGINNAME)
	cd /tmp; cp -r $(CURDIR) $(PLUGINNAME)
	rm -rf /tmp/$(PLUGINNAME)/tests
	rm -rf /tmp/$(PLUGINNAME)/tool_statistics/tests
	rm -rf /tmp/$(PLUGINNAME)/tool_water_balance/tests
	rm -rf /tmp/$(PLUGINNAME)/.git
	rm -rf /tmp/$(PLUGINNAME)/*.zip
	rm -rf /tmp/$(PLUGINNAME)/Docker
	rm -rf /tmp/$(PLUGINNAME)/docker-compose.yml
	rm -rf /tmp/$(PLUGINNAME)/docker-compose.override.yml
	rm -rf /tmp/$(PLUGINNAME)/external-dependencies/h5py
	rm -rf /tmp/$(PLUGINNAME)/external-dependencies/scipy
	rm -rf /tmp/$(PLUGINNAME)/deps
	rm -rf /tmp/$(PLUGINNAME)/__pycache__
	find /tmp/$(PLUGINNAME) -iname "*.pyc" -delete
	cd /tmp; zip -9r $(CURDIR)/$(PLUGINNAME).zip $(PLUGINNAME)

package: compile
	# Create a zip package of the plugin named $(PLUGINNAME).zip.
	# This requires use of git (your plugin development directory must be a
	# git repository).
	# To use, pass a valid commit or tag as follows:
	#   make package VERSION=Version_0.3.2
	@echo
	@echo "------------------------------------"
	@echo "Exporting plugin to zip package.	"
	@echo "------------------------------------"
	rm -f $(PLUGINNAME).zip
	git archive --prefix=$(PLUGINNAME)/ -o $(PLUGINNAME).zip $(VERSION)
	echo "Created package: $(PLUGINNAME).zip"

html:
	@echo
	@echo "------------------------------------"
	@echo "Building documentation using sphinx."
	@echo "------------------------------------"
	python3 scripts/generate-reference-docs.py
	cd doc; make html
	@echo "Open doc/build/html/index.html to see the documentation"


flake8:
	@echo "#### PEP8/pyflakes issues"
	@flake8 . --extend-exclude=deps
	@echo "No issues found."


beautiful:
	isort .
	black .
	flake8 .
