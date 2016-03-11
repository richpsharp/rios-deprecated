Release History
===============

1.1.16 (2016/03/11)
-------------------

* Allowing activity transition effectiveness to be floating point numbers rather than just 0 and 1.
* Removing the following unused outputs from RIOS:
    * [objective_x]\objective_level_transitions subdirectory and contents
    * continous_activity_portfolios subdirectory if budget_years == 1
    * yearly_activity_portfolios subdirectory if budget_years == 1


1.1.15 (2015/12/23)
-------------------

* Patching an issue that can occur in RIOS PORTER when a user provides a landcover map with an unsigned int datatype and a nodata value that exceeds 2^31.  In this case the nodata value is arbitrarily set to -9999 on the output PORTER landcover map.

1.1.14 (2015/10/26)
-------------------

* Patching an issue where a complicated RIOS run with many large raster files and many large vector files would cause RIOS to segfault when making the activity preference/mask layer during prioritization.

1.1.13 (2015/10/13)
-------------------

* Fixing an issue where a user could put zeros across the transition columns and the activity score would get an "nan" when dividing by the total weight.  Now setting denominator of weighted average to 1.0 in cases where the total weight sum is 0.0.

1.1.12 (2015/10/06)
-------------------

* Patching a LOGGER.debug syntax error on the disk sort routine.

1.1.11 (2015/10/04)
-------------------

* Addresses yet another memory issue related to large numbers of RIOS activities.

1.1.10 (2015/09/29)
-------------------

* Fixes another issue where too many activities and/or large input raster sizes would cause the buffering in the disk based sort to memory error.  Reduced the buffer item size from 40,000 per block to 1,024 per block.

1.1.9 (2015/09/25)
------------------

* Fixed an issue where large numbers of activities and/or large input raster sizes would cause a too many open files OS error on the prioritization step.  As an additional positive side effect, runtime performance of RIOS is slightly improved.


1.1.8 (2015/08/11)
------------------

* Fixed a bug that causes a PORTER crash when no ag or restoration transitions occur in IPA.
* Fixed internal import and pyinstaller errors that caused headaches when working on a local source branch.

1.1.7 (2015/08/07)
------------------

* Validating lulc coefficients table to ensure there is a field called 'description'.  If left out this caused a case where IPA ran normally but PORTER would crash looking for that field.

1.1.6 (2015/07/30)
------------------

* Patch to fix an issue where RIOS PORTER didn't launch and possibly an ImportError on "_superlu" on some machines.

1.1.5 (2015/07/17)
------------------

* Hotfix to rearrange references to RIOS Preprocessing tools on select RIOS IPA objective models.

1.1.4 (2015/07/17)
------------------

Previous releases of InVEST were from a Google Code site but was migrated in June 2015.  This is the first release of RIOS in less than ad hoc project structure.

* Restructured and refactored this repository from the one we used to have on
  Google code.
* Uses paver to handle builds, distribution, and archival of sample data.
* Uses pyinstaller to build frozen exes.
* Removed ArcGIS preprocessing toolbox and documentation from the installer since it was awkward for users to visit C:\Program Files\rios
* Updates to user interface for documentation and ArcGIS preprocessing links.
* Created a single command line interface to launch IPA and PORTER named rios_cli_{version}.exe
* Updated shortcut links in start menu to show the version of RIOS to be launched.
