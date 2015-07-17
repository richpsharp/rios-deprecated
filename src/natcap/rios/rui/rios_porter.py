"""This contains the user interface code for RIOS's RSAT."""

import sys
import logging
import os
import datetime
import json

from PyQt4 import QtGui, QtCore

import natcap.rios.rui

try:
    QString = QtCore.QString
except AttributeError:
    # For when we can't use API version 1
    QString = unicode

import pygeoprocessing.geoprocessing
from natcap.rios.rui import base_widgets
from natcap.rios import porter_core
import natcap.rios
import rios_ipa

logging.basicConfig(
    format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
    level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S ')

LOGGER = logging.getLogger('rios_porter')

#This is bad state variable that I need to use to determine if the rios
#workspace has been loaded or not
WORKSPACE_LOADED = False

class UndefinedTransitionAmount(Exception):
    """Raised when the user tries to create the scenarios but they
        haven't filled in a transition amount."""
    pass
class NoWorkspaceLoaded(Exception):
    """Raised when the user tries to create scenarios but hasn't
        loaded a workspace yet"""
    pass

def add_column(table, row_index, col_index, value):
    """Helper function to add a QTableWidgetItem with label 'value'
    at row_idnex/col_index in table"""
    item = QtGui.QTableWidgetItem(value)
    item.setFlags(QtCore.Qt.NoItemFlags)
    brush = QtGui.QBrush(QtGui.QColor(240, 240, 240))
    item.setBackground(brush)
    brush = QtGui.QBrush(QtGui.QColor(20, 20, 20))
    item.setForeground(brush)
    table.setItem(row_index, col_index, item)

def fill_table(qt_table, tuple_list):
    """Fills the rows and columns of a qt_table given a list of tuples that are
        passed in.  Each element in the tuple list corresponds to a row in
        the final table.  Any data previously in the table will be cleared.

        qt_table - a QTable
        tuple_list - a list of tuples to fill qt_table in.  each element will
            be a row and the values will be the positions in the tuple

        returns nothing"""

    qt_table.setRowCount(len(tuple_list))

    #Here we loop via indexes so we can fill in the table which needs
    #to know the row/column indexes.
    for row_index in range(len(tuple_list)):
        row_data = tuple_list[row_index]
        for col_index in range(len(row_data)):
            add_column(qt_table, row_index, col_index, str(row_data[col_index]))

class DropdownDelegate(QtGui.QStyledItemDelegate):
    dropdwn_options = []

    def createEditor(self, parent, option, index):
        dropdown = QtGui.QComboBox(parent)
        dropdown.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
        for option in self.dropdwn_options:
            dropdown.addItem(option)
        return dropdown

    def setModelData(self, editor, model, index):
        selection = editor.currentText()
        model.setData(index, selection, QtCore.Qt.EditRole)

class RsatWorkspaceFolder(base_widgets.FileEntry):
    """This is a class to hold the workspace folder for the sole purpose
        of registering a signal to a text change"""
    def __init__(self, attributes):
        super(RsatWorkspaceFolder, self).__init__(attributes)

class UpdateButton(QtGui.QPushButton, base_widgets.DynamicElement):
    def __init__(self, attributes):
        QtGui.QPushButton.__init__(self)
        base_widgets.DynamicElement.__init__(self, attributes)
        self.setText(attributes['label'])
        self.elements = [QtGui.QWidget(), QtGui.QWidget(), QtGui.QWidget(),
                         self]
        self.clicked.connect(self.update_workspace)

    def getOutputValue(self):
        return None

    def update_workspace(self, _):
        """This method is called when the user clicks the "load workspace"
            button.  It pulls out all the parts from the RIOS workspace
            and generates the UI tables that users can interact with"""

        LOGGER.info("attempting to load IPA workpace into PORTER")

        #Load core files from the RIOS run
        workspace_dir = self.root.allElements['workspace_dir'].value()
        results_suffix = self.root.allElements['results_suffix'].value()
        if results_suffix != '':
            results_suffix = '_' + results_suffix

        try:
            directory_file_registry_uri = os.path.join(
                workspace_dir, 'investment_portfolio_adviser_directory_' +
                'file_registry%s.json' % results_suffix)
            directory_file_registry_file = open(directory_file_registry_uri)
            directory_file_registry = json.load(directory_file_registry_file)
        except IOError:
            if results_suffix != '':
                error_message = (
                    "Can't find an IPA configuration file with the "
                    "results suffix '%s'.  Is it possible that the "
                    "results is spelled incorrectly?") % results_suffix
            else:
                error_message = ("Can't find an IPA configuration file in "
                                 "the workspace.")
            raise IOError(error_message)

        transition_type_uri = (
            directory_file_registry['file_registry']['transition_types_uri'])
        lulc_dataset_uri = (
            directory_file_registry['file_registry']['lulc_uri'])
        lulc_coefficients_file = (
            directory_file_registry['file_registry']['lulc_coefficients_table_uri'])

        transition_dataset_uri = (
            directory_file_registry['file_registry']
            ['max_transition_activity_portfolio_uri'])

        activity_portfolio_dataset_uri = (
            directory_file_registry['file_registry']['activity_portfolio_uri'])

        max_native_type_uri = (
            os.path.join(os.path.dirname(
                directory_file_registry['file_registry']
                ['activity_portfolio_uri']), 'max_native_type_id.tif'))

        #A dictionary of transition name -> type
        #(e.x. restoration -> agriculture)
        transition_types = porter_core.load_transition_types(
            transition_type_uri)

        #Make a lookup table of transition type to transition name
        transition_lookup = dict(
            [(value['raster_value'], key)
             for key, value in transition_types.iteritems()])

        #Build a list of restoration and agriculture types
        restoration_transition_list = []
        agriculture_transition_list = []
        for properties in transition_types.values():
            if properties['type'] == 'restoration':
                restoration_transition_list.append(properties['raster_value'])
            if properties['type'] == 'agriculture':
                agriculture_transition_list.append(properties['raster_value'])

        #Load the RIOS general LULC types.
        #Format is {lulc_name0: lulc_value0, ....}
        rios_lulc_general_table = porter_core.load_lulc_types(
            lulc_coefficients_file)

        #Build up a table that maps LULC names to their lulc ids, this is used
        #throughout the user interface below
        available_lulc_types = {}
        for lulc_id, lulc_dict in rios_lulc_general_table.iteritems():
            available_lulc_types[lulc_dict['name']] = lulc_id

        #Create the list of native lulc types by iterating through the
        #possible lulc_types dictionary and remembering those that are
        #marked as native
        native_type_list = []
        for lulc_id, lulc_dict in rios_lulc_general_table.iteritems():
            if lulc_dict['native']:
                native_type_list.append(lulc_id)

        #intersect available_lulcs with native_type_list to only get the list
        #that we're using now
        available_lulcs = (
            pygeoprocessing.geoprocessing.unique_raster_values_uri(
                lulc_dataset_uri))
        #Usually the lulcs load in as strings so convert them to ints
        available_lulcs = [int(x) for x in available_lulcs]

        ##Update Protection info on UI
        avoided_transition_dropdown = (
            self.root.allElements['avoided_transition_dropdown'].dropdown)
        avoided_transition_dropdown.clear()
        avoided_transition_dropdown.addItems(
            sorted(available_lulc_types.keys()))

        ##Build Restoration Table on UI
        #Get list of native transition tuples
        #('original lulc', 'transition name', 'new lulc')
        #For easier debugging insert 1.0 a default transition
        LOGGER.info('building native transition tuples')
        native_transition_tuples = porter_core.build_native_transition_tuples(
            lulc_dataset_uri, transition_dataset_uri,
            activity_portfolio_dataset_uri, native_type_list,
            restoration_transition_list, transition_lookup,
            rios_lulc_general_table, max_native_type_uri)

        restoration_table = self.root.allElements['restoration_table']
        fill_table(restoration_table, native_transition_tuples)

        ##Build agriculture table on UI
        LOGGER.info('building agriculture transition tuples')
        agriculture_transition_ids = porter_core.find_agriculture_transitions(
            lulc_dataset_uri, transition_dataset_uri,
            agriculture_transition_list, activity_portfolio_dataset_uri)

        agriculture_transitions = (
            [(rios_lulc_general_table[pair[0]]['name'],
              transition_lookup[pair[1]], pair[2])
             for pair in agriculture_transition_ids])

        LOGGER.debug(agriculture_transitions)
        agriculture_table = self.root.allElements['agriculture_table']
        agriculture_table.setEnabled(True)
        #Load all the agriculture transitions into the UI
        fill_table(agriculture_table, agriculture_transitions)

        #Add callbacks for the dropdown menus
        for row_index in range(len(agriculture_transitions)):
            #This part adds a callback so that when users click on the cell
            #they get a dropdown box that will be filled with lulc_types.
            lulc_label = QtGui.QTableWidgetItem('<click to set>')
            agriculture_table.setItem(row_index, 3, lulc_label)
            lulc_type_dropdown = DropdownDelegate()
            lulc_type_dropdown.dropdwn_options = sorted(
                available_lulc_types.keys())
            #We hard code this to column 2
            agriculture_table.setItemDelegateForColumn(3, lulc_type_dropdown)

        self.root.workspace_loaded = True
        self.root.messageArea.setError(False)
        self.root.messageArea.setText("RIOS workspace successfully loaded")

        #disable the workspace load button
        self.root.allElements['load_workspace_button'].setEnabled(False)


class RsatRegistrar(rios_ipa.WaterFundsRegistrar):
    def __init__(self, root_ptr):
        super(RsatRegistrar, self).__init__(root_ptr)

        changes = {
            'rsat_workspace_folder': RsatWorkspaceFolder,
            'button': UpdateButton
        }

        self.update_map(changes)

class RsatUI(base_widgets.ExecRoot):
    def __init__(self, uri, main_window):

        registrar = RsatRegistrar(self)

        version_help_label = QtGui.QLabel()
        version_help_label.setOpenExternalLinks(True)
        version_help_label.setAlignment(QtCore.Qt.AlignRight)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(version_help_label)

        base_widgets.ExecRoot.__init__(
            self, uri, layout, registrar, main_window, natcap.rios.__version__)

        main_window.setWindowTitle(self.attributes['label'])
        links = []
        links.append('RIOS version %s ' % (natcap.rios.__version__))
        doc_uri = 'http://www.naturalcapitalproject.org/rios_download.html'
        links.append('<a href=\"%s\">Download model documentation</a>' % doc_uri)
        feedback_uri = 'http://forums.naturalcapitalproject.org/'
        links.append('<a href=\"%s\">Report an issue</a>' % feedback_uri)
        version_help_label.setText(' | '.join(links))


        self.workspace_loaded = False
        self.okpressed = False
        self.show()


    def get_ui_args(self):
        self.messageArea.setError(False)
        self.messageArea.setText("Started translation at %s" %
                                 datetime.datetime.now().isoformat(' '))

        if not self.workspace_loaded:
            self.messageArea.setError(True)
            error_message = 'Load a RIOS workspace before continuing'
            self.messageArea.setText(error_message)
            raise NoWorkspaceLoaded(error_message)

        ui_args = self.assembleOutputDict()

        #Break down the ag table and restoration table here

        try:
            ui_args['agriculture_table'] = \
                build_table_dictionary(self.allElements['agriculture_table'])
            ui_args['restoration_table'] = \
                build_table_dictionary(self.allElements['restoration_table'])
        except UndefinedTransitionAmount as e:
            self.messageArea.setError(True)
            self.messageArea.setText(str(e))
            raise UndefinedTransitionAmount(e)

        return ui_args


    def save_to_python(self):
        """Save the current state of the UI to a python file after checking that
        there are no validation errors."""
        errors = self.errors_exist()
        if len(errors) > 0:
            self.error_dialog.set_messages(errors)
            self.error_dialog.exec_()
        else:
            warnings = self.warnings_exist()

            if len(warnings) > 0:
                self.warning_dialog.set_messages(warnings)
                exit_code = self.warning_dialog.exec_()

                # If the user pressed 'back' on the warning dialog, return to
                # the UI.
                if exit_code == 0:
                    return

            model = self.attributes['targetScript']
            model_name = model.split('.')[-1]

            filename = QtGui.QFileDialog.getSaveFileName(self, 'Select file to save...',
                '%s_parameters.py' % model_name, QString(),
                QString('Python file (*.py);;All files (*.* *)'))
            try:
                filename = unicode(filename)
            except TypeError:
                # can't cast unicode to unicode
                pass

            if filename != '':
                arguments = self.get_ui_args()
                invest_natcap.rui.fileio.save_model_run(arguments, model, filename)

    def queueOperations(self):
        ui_args = self.get_ui_args()

        self.operationDialog.exec_controller.add_operation(
            'model', ui_args, self.attributes['targetScript'])



def build_table_dictionary(table_table):
    table_dictionary = {}
    try:
        for row_index in xrange(table_table.rowCount()):
            row = []
            n_cols = table_table.columnCount()
            for col_index in xrange(n_cols):
                item = table_table.item(row_index, col_index)
                row.append(str(item.text()))
            table_dictionary[tuple(row[:-1])] = float(row[-1])
    except:
        error_message = "No proportion transition defined on row '%s' " % row
        raise UndefinedTransitionAmount(error_message)
    return table_dictionary


def launch_ui(sys_argv):
    """Used to launch the RIOS PORTER user interface

        sys_argv - a reference to sys.argv from a __main__ invokation"""
    APP = QtGui.QApplication(sys.argv)
    MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
    WINDOW = base_widgets.MainWindow(
        RsatUI, os.path.join(MODULE_DIR, 'rios_porter.json'))
    WINDOW.show()
    APP.exec_()
