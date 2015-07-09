"""RIOS IPA Launch Script"""

import sys
import pkg_resources

import natcap
import natcap.rios
import natcap.rios.iui.rios_ipa

import scipy.linalg.cython_blas
import scipy.linalg.cython_lapack
import scipy.special._ufuncs
import scipy.special._ufuncs_cxx

if __name__ == '__main__':
	print pkg_resources.get_distribution('natcap.rios').version
	natcap.rios.iui.rios_ipa.launch_ui(sys.argv)
