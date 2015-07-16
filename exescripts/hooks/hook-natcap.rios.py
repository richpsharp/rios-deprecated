from PyInstaller.hooks.hookutils import collect_data_files, collect_submodules
datas = collect_data_files('natcap.rios') + collect_data_files('natcap.rios.rui')
hiddenimports = collect_submodules('natcap.rios') + collect_submodules('natcap.rios.rui')
