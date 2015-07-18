"""This is the entry point to launch the RIOS UI"""

import os
import sys
import logging
import re

from PyQt4 import QtGui, QtCore

import natcap.rios
from natcap.rios.rui import base_widgets
from natcap.rios.rui import rui_validator
from natcap.rios.rui import fileio

import pygeoprocessing.geoprocessing

logging.basicConfig(format='%(asctime)s %(name)-5s %(levelname)-5s \
%(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S ')

LOGGER = logging.getLogger('natcap.rios.rios_ipa')


class WaterFundsRegistrar(base_widgets.ElementRegistrar):
    def __init__(self, root_ptr):
        super(WaterFundsRegistrar, self).__init__(root_ptr)

        changes = {'table': Table,
                   'tableEnabled': TableEnabled,
                   'vector': Vector,
                   'bin': Bin,
                   'binHeader': BinHeader,
                   'binList': BinList,
                   'binHeaderLULC': BinHeaderLULC,
                   'OGRFieldDropdown': OGRFieldDropdown,
                   'CSVFieldDropdown': CSVFieldDropdown,
                   'thievingHideableFile': ThievingHideableFileEntry,
                   'budgetConfigTable': BudgetConfigTable,
                   'linearInterpolatedBin': LinearlyInterpolatedBin,
                   'activityTransitionTable': ActivityTransitionTable,
                   'activityTableFile': RIOSActivityTableFileEntry
                  }

        self.update_map(changes)

class WaterFundsUI(base_widgets.ExecRoot):
    def __init__(self, uri, main_window):

        registrar = WaterFundsRegistrar(self)

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

        self.okpressed = False
        self.show()


    def queueOperations(self):
        ui_args = self.assembleOutputDict()
        self.operationDialog.exec_controller.add_operation('model', ui_args,
            self.attributes['targetScript'])

class BinList(base_widgets.GridList):
    def value(self):
        returnDict = {}
        for element in self.elements:
            if element.attributes['type'] == 'bin':
                returnDict[element.attributes['id']] = element.value()

        return returnDict

    def isEnabled(self):
        #this works for this single circumstance, where self.parent() is a
        #collapsible checkbox
        return self.parent().isChecked()

class Bin(base_widgets.DynamicPrimitive):
    def __init__(self, attributes):
        base_widgets.DynamicPrimitive.__init__(self, attributes)
        self.binLabel = QtGui.QLabel(self.attributes['label'])
        self.set_display_error(False)

        if 'range' in self.attributes:
            rangeMin = self.attributes['range'][0][0]
            rangeMax = self.attributes['range'][0][1]
        else:
            rangeMin = self.attributes['value']
            rangeMax = None

        self.rangeMin = QtGui.QLabel(str(rangeMin))
        self.rangeMax = QtGui.QLabel(str(rangeMax))
        for field in [self.rangeMin, self.rangeMax]:
            field.setWordWrap(True)

        self.weight = QtGui.QLabel(str(self.attributes['weight']))

        fields = []
        if 'range' in self.attributes:
            fields.append(('Bin minimum:', self.rangeMin))
            fields.append(('Bin maximum:', self.rangeMax))
            regexp = '([0-9]*\.?[0-9]+)|None'
        else:
            fields.append(('Bin values:', self.rangeMin))
            regexp = '[0-9]*[, 0-9]*'

        fields.append(('Weight:', self.weight))
        self.edit_button = BinEditButton('Edit', fields, regexp)

        self.elements = [self.binLabel, self.rangeMin, self.weight, self.edit_button]
        if 'range' in self.attributes:
            self.elements.insert(2, self.rangeMax)

    def value(self):
        values = {'weight' : float(self.weight.text())}
        if 'range' not in self.attributes:
            values['value'] = [int(r) for r in str(self.rangeMin.text()).split(', ')]
        else:
            def cast(x):
                if x != str(None):
                    return float(x)

            range_min = cast(self.rangeMin.text())
            range_max = cast(self.rangeMax.text())

            values['range'] = [[range_min, range_max], [True, False]]

        return values

class InterpolationBin(base_widgets.LabeledElement):
    def __init__(self, attributes):
        self.label =  str('Values will be interpolated based on raster min and max')
        self.output_dict = {'type': 'interpolated'}

        if 'label' not in attributes:
            attributes['label'] = self.label

        if 'showError' not in attributes:
            attributes['showError'] = False

        base_widgets.LabeledElement.__init__(self, attributes)

        # Add an empty spacer widget to make info buttons line up.
        self.addElement(QtGui.QWidget())

        if 'description_index' not in attributes:
            attributes['description_index'] = 1

        for i in range(attributes['description_index']):
                self.elements.insert(0, QtGui.QWidget())

    def isEnabled(self):
        return self.label.isEnabled()

    def value(self):
        return self.output_dict

class LinearlyInterpolatedBin(InterpolationBin):
    def __init__(self, attributes):
        self.label = str('Values will be linearly interpolated based on ' +
            'raster min and max')

        if 'inverted' in attributes:
            self.label += '. Results will be inverted.'

        InterpolationBin.__init__(self, attributes)
        if 'inverted' in attributes:
            self.output_dict['inverted'] = attributes['inverted']

        self.output_dict['interpolation'] = 'linear'
        self.output_dict['inverted'] = False

class BinEditButton(QtGui.QPushButton):
    def __init__(self, title, fields, regexp):
    #fields is a list of structure [(name1, field1), (name2, field2), ...]
        QtGui.QPushButton.__init__(self, title)

        self.dialog = BinEditDialog(fields, regexp)

        self.clicked.connect(self.edit_weight)
        self.setMaximumSize(50, 50)

    def edit_weight(self):
        self.dialog.show()

class BinEditDialog(QtGui.QDialog):
    def __init__(self, fields, regexp):
        QtGui.QDialog.__init__(self)

        self.setLayout(QtGui.QVBoxLayout())
        self.bin_widget = QtGui.QWidget()
        self.bin_widget.setLayout(QtGui.QGridLayout())
        self.layout().addWidget(self.bin_widget)
        self.fields = []
        reg_exp = QtCore.QRegExp(regexp)
        for row, field in enumerate(fields):
            field_label = field[0]
            field_reference = field[1]
            message = QtGui.QLabel(field_label)
            textfield = QtGui.QLineEdit()
            validator = QtGui.QRegExpValidator(reg_exp, textfield)
            textfield.setValidator(validator)
            self.fields.append((field_reference, textfield))

            self.bin_widget.layout().addWidget(message, row, 0, 1, 1)
            self.bin_widget.layout().addWidget(textfield, row, 1, 1, 1)

        self.button_box = QtGui.QDialogButtonBox()
        self.ok = QtGui.QPushButton(' Ok')
        self.cancel = QtGui.QPushButton(' Cancel')
        self.button_box.addButton(self.ok, self.button_box.AcceptRole)
        self.button_box.addButton(self.cancel, self.button_box.RejectRole)

        self.ok.clicked.connect(self.save)
        self.cancel.clicked.connect(self.close)

        self.layout().addWidget(self.button_box)

    def showEvent(self, data=None):
        for field_reference, dialog_field in self.fields:
            dialog_field.setText(field_reference.text())

    def save(self):
        for field_reference, dialog_field in self.fields:
            text = re.sub('[, ]+', ', ', str(dialog_field.text()))
            text = re.sub('^, |, $', '', text)
            field_reference.setText(text)
        self.closeEvent(QtGui.QCloseEvent())

class BinHeader(base_widgets.DynamicPrimitive):
    def __init__(self, attributes):
        base_widgets.DynamicPrimitive.__init__(self, attributes)
        self.set_display_error(False)
        self.binLabel = QtGui.QLabel('<b>Bin label</b>')
        self.rangeMin = QtGui.QLabel('<b>Bin minimum</b>')
        self.rangeMax = QtGui.QLabel('<b>Bin maximum</b>')
        self.weight = QtGui.QLabel('<b>Weight</b>')

        self.elements = [self.binLabel, self.rangeMin, self.rangeMax, self.weight]

class BinHeaderLULC(BinHeader):
    def __init__(self, attributes):
        BinHeader.__init__(self, attributes)
        self.set_display_error(False)
        self.rangeMin = QtGui.QLabel('<b>Bin value</b>')

        self.elements = [self.binLabel, self.rangeMin, self.weight]


class AbstractTable(QtGui.QTableWidget, base_widgets.DynamicPrimitive):
    class Row(base_widgets.DynamicPrimitive):
        def __init__(self, attributes, rowNum, parentTable):
            base_widgets.DynamicPrimitive.__init__(self, attributes)
            self.rowNum = rowNum
            self.parentTable = parentTable

        def value(self):
            # Skipping this for the time being.  See issue 765.
            return None

        def setState(self, state):
            if state == True:
                self.parentTable.showRow(self.rowNum)
            else:
                self.parentTable.hideRow(self.rowNum)

        def get_label(self):
            if 'label' in self.attributes:
                id = self.attributes['label']
                if hasattr(self.parentTable.root, 'allElements'):
                    if id in self.parentTable.root.allElements:
                        return self.parentTable.root.allElements[id].attributes['label']
                return id
            else:
                return ''

        def add_column(self, col_num):
            """To be called whenever a column is added.  This is a placeholder
            function to be overridden as necessary by/for subclasses."""
            pass

        def setValue(self, default_value):
            """If default_value is a list, assume that it has as many elements
            as there are columns.  Otherwise (if this value is a scalar), assume
            that all cells in this row should have the same default value."""
            if not isinstance(default_value, list):
                default_value = [default_value for r in
                    range(self.parentTable.columnCount())]

            for col_index, value in enumerate(default_value):
                item = self.parentTable.item(self.rowNum, col_index)

                #disable the cell if the value for this column is None
                #represented as null in the json configuration
                if value == None:
                    self.parentTable.grey_out_item(item)

                if item == None:
                    item = QtGui.QTableWidgetItem()
                    self.parentTable.setItem(self.rowNum, col_index, item)

                if item.flags() != QtCore.Qt.NoItemFlags:
                    widget = self.parentTable.cellWidget(self.rowNum, col_index)
                    if widget == None:
                        self.set_value_func(item, value)
                    else:
                        self.set_value_func(widget, value)

        def set_value_func(self, item, value):
            # Only set the text in this item if nothing has been set already.
            if str(item.text()) == '':
                item.setText(str(value))

    def __init__(self, attributes):
        QtGui.QTableWidget.__init__(self)
        base_widgets.DynamicPrimitive.__init__(self, attributes)
        self.rows = []

        if 'fixedHeight' not in self.attributes:
            self.attributes['fixedHeight'] = True

        if 'striped' not in self.attributes:
            self.attributes['striped'] = True

        self.makeRows()    # build rows from json attributes
        self.makeColumns() # build columns from json attributes

        self.setShowGrid(True)
        self.resizeColumnsToContents()

        self.setAlternatingRowColors(self.attributes['striped'])
        self.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        self.verticalHeader().setResizeMode(QtGui.QHeaderView.Fixed)
        self.setSizePolicy(QtGui.QSizePolicy.Preferred,
                           QtGui.QSizePolicy.Minimum)
        self.updateGeometry()
        self.set_exclusions()

    def setState(self, state, includeSelf=True, recursive=True):
        if 'columnsSetBy' in self.attributes:
            element_id = self.attributes['columnsSetBy']
            element_ptr = root_ptr.find_element_ptr(element_id)
            element_ptr.enableColumns.append(self)
        base_widgets.DynamicPrimitive.setState(self, state, includeSelf, recursive)

    def setEnabled(self, state):
        if 'columnsSetBy' in self.attributes:
            element_id = self.attributes['columnsSetBy']
            element_ptr = root_ptr.find_element_ptr(element_id)
            element_ptr.enableColumns.append(self)

        base_widgets.DynamicPrimitive.setEnabled(self, state)

    def resetValue(self):
        for row in self.rows:
            row.resetValue()

    def setValue(self, value):
        """Value must be a dictionary with the following structure:
            'rows': a list of python string labels
            'columns': a list of python string labels
            'data' a python list of lists.  ordering is:
                value['data'][row][column]"""

        try:
            self.set_row_labels(value['rows'])
            self.set_col_labels(value['columns'])
            for row_index, row_list in enumerate(value['data']):
                for col_index, col in enumerate(row_list):
                    self.item(row_index, col_index).setText(str(col))
        except TypeError:
            # Thrown when setting all rows to a scalar default value
            for row in self.rows:
                row.setValue(value)


    def get_header_height(self):
        max_newlines = 0
        for column in self.attributes['columns']:
            col_header = column['label']
            num_newlines = col_header.count('\n') + 1 #account for exist. line
            if num_newlines >= max_newlines:
                max_newlines = num_newlines

        return max_newlines * 20

    def set_exclusions(self):
        for col_index, column in enumerate(self.attributes['columns']):
            for row_index, row in enumerate(self.attributes['rows']):
                item = self.item(row_index, col_index)
                set_item = False
                if item == None:
                    item = QtGui.QTableWidgetItem()
                    set_item = True

                if 'excludeFrom' in row:
                    if column['label'] in row['excludeFrom']:
                        self.grey_out_item(item)

                if set_item:
                    self.setItem(row_index, col_index, item)

    def grey_out_item(self, item):
        item.setFlags(QtCore.Qt.NoItemFlags)
        brush = QtGui.QBrush(QtGui.QColor(200, 200, 200))
        item.setBackground(brush)
        item.setText('')


    def clearRows(self):
        for row in self.rows:
            self.removeRow(row.rowNum)
        self.rows = []

    def buildRow(self, attributes, index):
        return self.Row(attributes, index, self)

    def add_row(self, attributes=None):
        if attributes == None:
            try:
                default_val = self.attributes['defaultValue']
            except KeyError:
                default_val = 0.0
            attributes = {'id': 'new_row', 'label': 'new_row',
                          'defaultValue': default_val}

        num_rows = len(self.rows)
        new_row = self.buildRow(attributes, num_rows)
        self.rows.append(new_row)

    def makeRows(self):
        """Build row objects from the json configuration."""
        self.clearRows()

        numRows = 0
        for index, rowAttributes in enumerate(self.attributes['rows']):
            newRow = self.buildRow(rowAttributes, index)
            self.rows.append(newRow)
            numRows += 1

        row_labels = [row['label'] for row in self.attributes['rows']]
        self.set_row_labels(row_labels)
        self.setRowCount(numRows)

    def set_row_labels(self, labels):
        """If labels are a python list of strings, set row labels to those."""
        regexp = "[\n]"

        current_row_count = self.rowCount()
        if len(labels) > len(self.rows):
            new_rows = len(labels) - len(self.rows)
            for i in range(new_rows):
                self.add_row()

        rowLabels = self.makeQStringList(labels, regexp)
        self.setRowCount(len(rowLabels))
        self.setVerticalHeaderLabels(rowLabels)
        self.resetValue()

    def set_col_labels(self, labels):
        """Se the column labels to the labels passed in to 'labels'.  This
        function also creates columns as necessary."""
        column_count = len(labels)

        current_col_count = self.columnCount()
        if current_col_count < column_count:
            num_new_cols = column_count - current_col_count
            for i in range(num_new_cols):
                self.add_column(i + current_col_count)

        column_labels = self.makeQStringList(labels)
        self.setColumnCount(column_count)
        self.setHorizontalHeaderLabels(column_labels)
        self.resetValue()

    def add_column(self, index=None):
        """Append a column to the existing columns"""
        if index == None:
            index = self.columnCount()

        for row in self.rows:
            row.add_column(index)

    def makeColumns(self):
        """Build columns from json attributes."""
        column_count = len(self.attributes['columns'])
        column_labels = self.makeQStringList(self.attributes['columns'])
        labels = [col['label'] for col in self.attributes['columns']]
        self.set_col_labels(labels)

    def column_labels(self):
        return [str(self.horizontalHeaderItem(col).text()) for col in
                range(self.columnCount())]

    def row_labels(self):
        return [str(self.verticalHeaderItem(row).text()) for row in
                range(self.rowCount())]

    def makeQStringList(self, list, regexp=''):
        #returns a qstringlist
        qslist = QtCore.QStringList()
        for row in list:
            if isinstance(row, dict):
                label = row['label']
            elif isinstance(row, self.Row):
                label = row.get_label()
            else:
                label = row
            label = re.sub(regexp, '', label)
            qslist.append(label)

        return qslist

    def getElementsDictionary(self):
        #need a custom implementation here so that we can add pointers to rows
        #to the elements dictionary, since rows are separate objects.
        elements = base_widgets.DynamicPrimitive.getElementsDictionary(self)

        for row in self.rows:
            elements[row.attributes['id']] = row

        return elements

    def sanitize(self, string):
        del_chars = "[()\n]"
        string = re.sub(del_chars, '', string)

        bad_chars = "[^a-zA-Z0-9_ ]"
        return re.sub(bad_chars, '_', string)

    def value(self):
        # The output value of the table is not actually maintained by the table
        # object itself, but rather is maintained by its rows, which are
        # saved separately.
        table_data = []
        row_labels = self.row_labels()
        column_labels = self.column_labels()

        for row_index, row_label in enumerate(row_labels):
            row = []
            for column_index, column_label in enumerate(column_labels):
                item = self.item(row_index, column_index)
                row.append(str(item.text()))
            table_data.append(row)

        return {'rows': row_labels, 'columns': column_labels,
                'data': table_data}

    def getOutputValue(self):
        outputDict = {}
        #for each column
        for col in range(self.columnCount()):
            header = self.horizontalHeaderItem(col)
            header_label = unicode(header.text())
            try:
                json_label = self.attributes['columns'][col]['label']
                if unicode(header.text()) != json_label:
                    col_text = str(header.text())
                else:
                    if 'file_name' in self.attributes['columns'][col]:
                        col_text = self.attributes['columns'][col]['file_name']
                    else:
                        col_text = self.sanitize(header_label)
            except IndexError:
                col_text = unicode(header.text())

            outputDict[col_text] = {}

            for row in range(self.rowCount()):
                if not self.isRowHidden(row):
                    # Check to see if the row header text differs from the
                    # attributes label.  If so, extract and use for args_id
                    row_item = self.verticalHeaderItem(row)
                    try:
                        json_row_label = self.attributes['rows'][row]['label']
                        if str(row_item.text()) != json_row_label:
                            args_id = str(row_item.text())
                        else:
                            if 'output_id' in self.attributes['rows'][row]:
                                args_id = self.attributes['rows'][row]['output_id']
                            elif 'file_name' in self.attributes['rows'][row]:
                                args_id = self.attributes['rows'][row]['file_name']
                            else:
                                args_id = unicode(row_item.text())
                    except IndexError:
                        args_id = unicode(row_item.text())

                    cell_item = self.cellWidget(row, col)
                    if cell_item == None:
                        cell_item = self.item(row, col) #returns None if the cell is empty

                    if isinstance(cell_item, QtGui.QComboBox):
                        text = unicode(cell_item.currentText())
                    else:
                        text = unicode(cell_item.text())
                        #text will be an empty string if the cell_item is one of
                        #the cells that are excluded in the json file.
                        try:
                            if unicode(text) == '':
                                text = 0.0
                            else:
                                text = float(text)
                        except ValueError:
                            #This might be the case where there's a leading
                            #astrix, this is okay, but just check...
                            pass

                    outputDict[col_text][args_id] = text

        return outputDict

    def isEnabled(self):
        print 'checking isEnabled'
        if len(self.rows) > 0:
            return True
        return False

    def requirementsMet(self):
        #check that each enabled row has something in each cell
        for col in range(self.columnCount()):
            for row in range(self.rowCount()):
                if not self.isRowHidden(row):
                    cell_item = self.item(row, col)
                    if not cell_item:
                        print 'cell at ' + str(row) + ' ' + str(col) + ' is empty'
                        return False
        return True

    def setBGcolorSatisfied(self, state):
        print 'table satisfied: ' + str(state)


class Table(AbstractTable):
    class NumbersOnlyDelegate(QtGui.QStyledItemDelegate):
        def createEditor(self, parent, option, index):
            lineEdit = QtGui.QLineEdit(parent)
            regexpObj = QtCore.QRegExp('\~?[0-9]*\\.?[0-9]*')
            validator = QtGui.QRegExpValidator(regexpObj, lineEdit)
            lineEdit.setValidator(validator)

            return lineEdit

    def __init__(self, attributes):
        AbstractTable.__init__(self, attributes)
        self.setItemDelegate(self.NumbersOnlyDelegate())
        self.setEditTriggers(QtGui.QAbstractItemView.AllEditTriggers)

class TableEnabled(Table):
    def isEnabled(self):
        return True

class BudgetConfigTable(Table):
    class DropdownDelegate(QtGui.QStyledItemDelegate):
        dropdwn_options = []

        def createEditor(self, parent, option, index):
            dropdown = QtGui.QComboBox(parent)
            for option in self.dropdwn_options:
                dropdown.addItem(option)
            return dropdown

        def setModelData(self, editor, model, index):
            selection = editor.currentText()
            model.setData(index, selection, QtCore.Qt.EditRole)

    def __init__(self, attributes):
        Table.__init__(self, attributes)
        for index, row in enumerate(self.attributes['rows']):
            try:
                row_type = row['type']
                if row_type == 'dropdown':
                    delegate = self.DropdownDelegate()
                    delegate.dropdwn_options = row['options']
                    self.setItemDelegateForRow(index, delegate)
            except KeyError:
                pass

class ActivityTransitionTable(Table):
    class CheckBoxDelegate(QtGui.QStyledItemDelegate):
        def createEditor(self, parent, option, index):
            return QtGui.QCheckBox(parent)

        def setEditorData(self, editor, index):
            checked = index.model().data(index,
                QtCore.Qt.DisplayRole).toString()
            if checked == '1':
                editor.setCheckState(QtCore.Qt.Checked)
            else:
                editor.setCheckState(QtCore.Qt.Unchecked)

        def setModelData(self, editor, model, index):
            if editor.checkState() == QtCore.Qt.Checked:
                text = 1
            else:
                text = 0
            model.setData(index, text)

        def paint(self, painter, option, index):
            value = index.model().data(index).toInt()[0]
            if value == 1:
                option.font.setBold(True)
                option.font.setItalic(True)
            QtGui.QStyledItemDelegate.paint(self, painter, option, index)

    def __init__(self, attributes):
        Table.__init__(self, attributes)
        self.setItemDelegate(self.CheckBoxDelegate())

class Vector(Table):
    def getOutputValue(self):
        outputDict = {}
        #for each column
        for col in range(self.columnCount()):
            header = self.horizontalHeaderItem(col)
            header_label = self.sanitize(str(header.text()))
            if str(row_item.text()) != self.attributes['columns'][col]['label']:
                col_text = str(row_item.text())
            else:
                if 'file_name' in self.attributes['columns'][col]:
                    col_text = self.attributes['columns'][col]['file_name']
                else:
                    col_text = self.sanitize(header_label)

            cell_item = self.item(0, col)
            if not cell_item:
                cell_value = 0.0
            else:
                cell_value = cell_item.text()
                if cell_value == '':
                    cell_value = 0.0

            outputDict[col_text] = float(cell_value)
        return outputDict

class RIOSActivityTableFileEntry(base_widgets.FileEntry):
    def __init__(self, attributes):
        base_widgets.FileEntry.__init__(self, attributes)
        self.handler = None
        self.textField.textChanged.connect(self.update_handler)
        self.activity_names = []
        self.embedded_uis = []
        self.column_triggers = []
        self.row_triggers = []

    def setValue(self, text):
        base_widgets.FileEntry.setValue(self, text)
        try:
            self.update_handler()
        except:
            pass

    def getOutputValue(self):
        output_dict = {}

        lulc_table_lookup = pygeoprocessing.geoprocessing.get_lookup_from_csv(
            self.value(), 'lucode')

        for lucode, lookup_table in lulc_table_lookup.iteritems():
            output_dict[lucode] = []
            for key in lookup_table.keys():
                if key in self.activity_names and lookup_table[key] == 1:
                    output_dict[lucode].append(key)

        LOGGER.debug(output_dict)

        return output_dict

    def update_handler(self, event=None):
        # Check the validator's error.  If error was present, skip updating the
        # handler.
        error = self.validator.get_error()
        if error != (None, None):
            return

        #self.value() is the path to the table in the input field
        lulc_table_lookup = pygeoprocessing.geoprocessing.get_lookup_from_csv(
            self.value(), 'lucode')

        #keep every column that has only 0's and 1's
        self.activity_names = []
        for column_key in lulc_table_lookup.itervalues().next().keys():
            valid_activity_column = True
            for lulc in lulc_table_lookup.iterkeys():
                if lulc_table_lookup[lulc][column_key] not in [0, 1]:
                    valid_activity_column = False
                    break
            if valid_activity_column:
                self.activity_names.append(column_key)

        #create a dictionary indexed by lulc code and only has activity names


        try:
            if self.column_triggers == []:
                for element_id in self.attributes['triggerColumns']:
                    self.column_triggers.append(self.root.obj_registrar.root_ui.find_element_ptr(element_id))
        except KeyError:
            pass

        try:
            if self.row_triggers == []:
                for element_id in self.attributes['triggerRows']:
                    self.row_triggers.append(self.root.obj_registrar.root_ui.find_element_ptr(element_id))
        except KeyError:
            pass

        for table in self.column_triggers:
            table.set_col_labels(self.activity_names)

        for table in self.row_triggers:
            table.set_row_labels(self.activity_names)

class TableHandler(base_widgets.Dropdown):
    def __init__(self, attributes):
        base_widgets.Dropdown.__init__(self, attributes)
        self.handler = None  # this should be set in an appropriate subclass.
        self.uri = ''

    def populate_fields(self):
        self.dropdown.clear()
        self.handler.update(self.enabledBy.value())
        field_names = self.handler.get_fieldnames(case='orig')
        for name in field_names:
            self.dropdown.addItem(name)

    def setState(self, state, includeSelf=True, recursive=True):
        base_widgets.Dropdown.setState(self, state, includeSelf, recursive)

        if state == False:
            self.dropdown.clear()
        else:
            self.populate_fields()

class CSVFieldDropdown(TableHandler):
    def __init__(self, attributes):
        TableHandler.__init__(self, attributes)
        self.handler = fileio.CSVHandler(self.uri)

class OGRFieldDropdown(TableHandler):
    def __init__(self, attributes):
        TableHandler.__init__(self, attributes)
        self.handler = fileio.OGRHandler(self.uri)

class ThievingHideableFileEntry(base_widgets.HideableFileEntry):
    def __init__(self, attributes):
        base_widgets.HideableFileEntry.__init__(self, attributes)
        self.get_value_from = None

    def updateLinks(self, rootPointer):
        base_widgets.HideableFileEntry.updateLinks(self, rootPointer)
        self.get_source_ptr()

    def get_source_ptr(self):
        target_id = self.attributes['getValueFrom']
        self.get_value_from = self.root.find_element_ptr(target_id)

    def value(self):
        if self.get_value_from == None:
            self.get_source_ptr()

        if not self.checkbox.isChecked():
            return self.get_value_from.value()
        else:
            return base_widgets.HideableFileEntry.value(self)

def launch_ui(sys_argv):
    """Used to launch the RIOS IPA user interface

        sys_argv - a reference to sys.argv from a __main__ invokation"""

    APP = QtGui.QApplication(sys.argv)
    MODULE_DIR = os.path.dirname(os.path.realpath(__file__))
    WINDOW = base_widgets.MainWindow(
        WaterFundsUI, os.path.join(MODULE_DIR, 'rios_ipa.json'))
    WINDOW.show()
    APP.exec_()
