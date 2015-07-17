Release History
===============

1.1.4
-----

Previous releases of InVEST were from a Google Code site but was migrated in June 2015.  This is the first release of RIOS in less than ad hoc project structure.

* Restructured and refactored this repository from the one we used to have on
  Google code.
* Uses paver to handle builds, distribution, and archival of sample data.
* Uses pyinstaller to build frozen exes.
* Removed ArcGIS preprocessing toolbox and documentation from the installer since it was awkward for users to visit C:\Program Files\rios
* Updates to user interface for documentation and ArcGIS preprocessing links.
* Created a single command line interface to launch IPA and PORTER named rios_cli_{version}.exe
* Updated shortcut links in start menu to show the version of RIOS to be launched.
