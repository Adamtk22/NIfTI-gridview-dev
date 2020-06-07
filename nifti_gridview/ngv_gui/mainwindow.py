import sys
from PySide2.QtWidgets import QMainWindow, QWidget, QProgressBar, QErrorMessage, \
    QFileDialog, QTableWidgetItem, QColorDialog
from PySide2.QtCore import SIGNAL, SLOT, Signal, Slot, QStringListModel, Qt
from PySide2.QtGui import QImage, QPixmap, QColor
from ._mainwindow import *
from ngv_io import ngv_io_reader_wrapper, ngv_io_writer_wrapper
from visualization import draw_grid_wrapper, colormaps

import numpy as np
import cv2
import logging as lg
import os

class ngv_mainwindow(QMainWindow, QWidget):
    def __init__(self,parent=None):
        super(ngv_mainwindow, self).__init__(parent)
        self.ui = Ui_ngv_mainwindow()
        self.ui.setupUi(self)

        # Add progress bar to statusbar
        self._status_bar = self.statusBar()
        self._progress_bar = QProgressBar(self.statusBar())
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setValue(100)
        self.statusBar().addPermanentWidget(self._progress_bar)

        # TODO: Move cache to a class for memory managements
        self._image_cache = {}


        #TODO: Logger

        # self.ui.files_listWidget.additem
        # Manual bar
        # - Open folder
        # - Open folder for segmentations
        # - Save configurations
        # - Export images
        # self.main_menu = self.menuBar()
        # self._file_OpenFolder = self.main_menu.addMe

        # Left panel
        # - Toolbox
        # - Listview of images

        # set up UI layouts
        # self._left_panel = QStackedLayout()
        self.ui.actionOpen_Folder.triggered.connect(self._action_open_folder)
        self.ui.actionExport_Images.triggered.connect(self._action_export_images)
        self.ui.actionOpen_Segmentation_Folder.triggered.connect(self._action_open_segmentation_folder)

        # Set up io object
        self.draw_worker = draw_grid_wrapper(self)
        self.io_reader_worker = ngv_io_reader_wrapper(self)
        self.io_write_worker = ngv_io_writer_wrapper(self)
        self.io_reader_worker.update_progress.connect(self._update_progress)
        self.io_reader_worker.display_msg.connect(self._show_message)
        self.io_write_worker.display_msg.connect(self._show_message)
        self.io_seg_workers = []


        # Set up drawer
        self.ui.files_listWidget.itemSelectionChanged.connect(self._update_image_data)

        # connect spinbox
        self.checkbox_connectionmap = {self.ui.checkBox_userange: [self.ui.spinBox_drawrange_lower,
                                                                   self.ui.spinBox_drawrange_upper],
                                       self.ui.checkBox_autonrow: [self.ui.spinBox_nrow]}
        self.ui.checkBox_autonrow.stateChanged.connect(self._toggle_checkboxes)
        self.ui.checkBox_userange.stateChanged.connect(self._toggle_checkboxes)
        self.ui.checkBox_autonrow.stateChanged.connect(self._update_image_data)
        self.ui.checkBox_userange.stateChanged.connect(self._update_image_data)
        self.ui.spinBox_nrow.valueChanged.connect(self._update_image_data)
        self.ui.spinBox_offset.valueChanged.connect(self._update_image_data)
        self.ui.spinBox_drawrange_upper.valueChanged.connect(self._update_image_data)
        self.ui.spinBox_drawrange_lower.valueChanged.connect(self._update_image_data)
        self.ui.spinBox_padding.valueChanged.connect(self._update_image_data)


        # connect drawing worker
        self.draw_worker.finished.connect(self._update_displayed_img)
        self.draw_worker.display_msg.connect(self._show_message)
        self._show_message(self.tr('Ready.'))


        # Connect tablewidget
        self.ui.tableWidget_segmentations.itemDoubleClicked.connect(self._select_color)

        ######################
        # Initialize UI
        ######################
        w = self.ui.tableWidget_segmentations.width()
        for i in range(5):
            self.ui.tableWidget_segmentations.setColumnWidth(i, w / 5)

        self.ui.comboBox_cmap.addItems(list(colormaps.keys()))
        self.ui.comboBox_cmap.setCurrentText('Default')

        ##################################
        # Connection after UI initialized
        ##################################
        self.ui.comboBox_cmap.currentTextChanged.connect(self._update_image_data)

    @Slot(str)
    def _show_message(self, s):
        self._status_bar.showMessage(s)

    def _toggle_checkboxes(self):
        target = self.checkbox_connectionmap[self.sender()]
        for spinbox in target:
            if spinbox.isEnabled():
                spinbox.setEnabled(False)
            else:
                spinbox.setEnabled(True)


    def _update_progress(self, val):
        self._progress_bar.setDisabled(False)
        self._progress_bar.setValue(val)
        if val == 100:
            self._status_bar.showMessage('Ready.')


    def _update_file_list_view(self):
        """
        Push file names keys into the list view.
        """
        self.ui.files_listWidget.clear()
        for key in self.io_reader_worker._reader._files.keys():
            self.ui.files_listWidget.addItem(key)
        self.ui.files_listWidget.sortItems()


    def _action_open_folder(self):
        """
        Read nii.gz and push items into list view widget.
        """

        fd = QFileDialog(self)
        reader_root_dir = fd.getExistingDirectory(self, self.tr("Open"),
                                                  '/home/***REMOVED***/Source/Repos/***REMOVED***_Segmentation/***REMOVED***_Segmentation',
                                                  QFileDialog.ShowDirsOnly)
        self.io_reader_worker.configure_reader(reader_root_dir, True)
        self._update_file_list_view()

        # Allow loading segmentations afterwards
        self.ui.actionOpen_Segmentation_Folder.setEnabled(True)

    def _action_open_segmentation_folder(self):
        fd = QFileDialog(self)
        reader_root_dir = fd.getExistingDirectory(self, self.tr("Open"),
                                                  '/home/***REMOVED***/Source/Repos/***REMOVED***_Segmentation/***REMOVED***_Segmentation',
                                                  QFileDialog.ShowDirsOnly)

        if not os.path.isdir(reader_root_dir):
            return

        seg_loader = ngv_io_reader_wrapper()
        seg_loader.configure_reader(reader_root_dir, True, dtype='uint8')

        self.io_seg_workers.append(seg_loader)

        # Add item to table
        row_num = self.ui.tableWidget_segmentations.rowCount()
        row_identifier = QTableWidgetItem(os.path.basename(reader_root_dir))
        row_identifier.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        row_color_widget = QTableWidgetItem()
        row_color_widget.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        row_color_widget.setBackgroundColor(QColor(255, 255, 0))

        self.ui.tableWidget_segmentations.insertRow(self.ui.tableWidget_segmentations.rowCount())
        self.ui.tableWidget_segmentations.setItem(row_num, 0, row_color_widget)
        self.ui.tableWidget_segmentations.setItem(row_num, 1, row_identifier)

        # Update display
        if len(self.ui.files_listWidget.selectedItems()) == 0:
            self.ui.files_listWidget.setCurrentItem(self.ui.files_listWidget.itemAt(0, 0))
        else:
            self._update_image_data()



    def _update_image_data(self):
        """Triggered when list widget item changed. Load image into cache."""
        active_file = self.ui.files_listWidget.selectedItems()[0].text()
        target_im = self.io_reader_worker[active_file]

        # Handle display range
        if  self.ui.checkBox_userange.isChecked():
            # Range check
            display_lrange = self.ui.spinBox_drawrange_lower.value()
            display_urange = self.ui.spinBox_drawrange_upper.value()
            self.ui.spinBox_drawrange_lower.setMaximum(display_urange - 2)
            self.ui.spinBox_drawrange_upper.setMinimum(display_lrange + 2)
            self.ui.spinBox_drawrange_upper.setMaximum(target_im.shape[0] - 1)
            target_im = target_im[display_lrange:display_urange + 1]
        else:
            # Resume original range if not checked
            self.ui.spinBox_drawrange_lower.blockSignals(True)
            self.ui.spinBox_drawrange_upper.blockSignals(True)
            self.ui.spinBox_drawrange_lower.setValue(0)
            self.ui.spinBox_drawrange_upper.setValue(target_im.shape[0] - 1)
            self.ui.spinBox_drawrange_lower.blockSignals(False)
            self.ui.spinBox_drawrange_upper.blockSignals(False)


        # calculate nrow if auto checked
        if self.ui.checkBox_autonrow.isChecked():
            nrow = int(np.sqrt(target_im.shape[0]))
        else:
            nrow = self.ui.spinBox_nrow.value()

        config = {
            'target_im': target_im,
            'segment_color': [self.ui.tableWidget_segmentations.itemAt(i, 0).background() \
                              for i in range(self.ui.tableWidget_segmentations.rowCount())],
            'nrow': nrow,
            'offset': self.ui.spinBox_offset.value(),
            'margins': self.ui.spinBox_padding.value(),
            'cmap': self.ui.comboBox_cmap.currentText(),
            'thickness': 2
        }
        for s in self.io_seg_workers:
            if not 'segment' in config:
                config['segment'] = []
            seg_temp = s[active_file]
            config['segment'].append(seg_temp)

        self.draw_worker.set_config(config)
        self.draw_worker.start()
        # self.draw_worker.run()

    def _action_export_images(self):
        """
        Export images as either .png or .jpg to the destination folder using the current configuration.
        """
        # Error check
        if self.ui.files_listWidget.count() == 0:
            mb = QErrorMessage(self)
            mb.showMessage(self.tr("Please specify source image directories first!"))
            return

        if self.io_write_worker.isRunning():
            mb = QErrorMessage(self)
            mb.showMessage(self.tr("Export in progress already."))
            return

        # There are no config if no images are selected, so we go ahead and activate one.
        if len(self.ui.files_listWidget.selectedItems()) == 0:
            self.ui.files_listWidget.setCurrentItem(self.ui.files_listWidget.itemAt(0, 0))

        writer_draw_worker = draw_grid_wrapper(self.io_write_worker)
        writer_draw_worker.set_config(self.draw_worker._config)
        write_dir = QFileDialog.getExistingDirectory(self, self.tr("Write Image"))

        if not os.path.isdir(write_dir):
            self._show_message("No directory supplied!")
            return

        self.io_write_worker.configure_writer(self.io_reader_worker, self.io_seg_workers,
                                              writer_draw_worker, write_dir)
        self.io_write_worker.start()


    def _update_displayed_img(self):
        # convert result to QT
        displayim = self.draw_worker.get_result()
        if not isinstance(displayim, np.ndarray):
            displayim = np.array(displayim)
        qImg = self._np_to_QPixmap(displayim)
        self._image_cache['current'] = qImg

        # TODO: Cahce this image data somewhere, display and scale on another slot, also triggered by scaling.
        self.ui.image_label.setPixmap(qImg.scaledToHeight(self.ui.image_label.height()))

    @Slot(QTableWidgetItem)
    def _select_color(self, item):
        if not isinstance(item, QTableWidgetItem):
            raise ValueError

        if item.text() != "":
            return

        color = QColorDialog().getColor()
        if not color.isValid():
            item.setSelected(False)
            return

        item.setBackgroundColor(color)
        item.setSelected(False)

        self._update_image_data()

    def resizeEvent(self, *args, **kwargs):
        """Inherit and change behavior for resizing"""
        super(ngv_mainwindow, self).resizeEvent(*args, **kwargs)

        # Change displayed image size according to height
        if 'current' in self._image_cache:
            pixmap = self._image_cache['current']
            self.ui.image_label.setPixmap(pixmap.scaledToHeight(self.ui.image_label.height()))

        w = self.ui.tableWidget_segmentations.width()
        for i in range(5):
            self.ui.tableWidget_segmentations.setColumnWidth(i, w / 5)


    @staticmethod
    def _np_to_QPixmap(inim):
        """Convert numpy uint8 image to QPixmap"""
        assert isinstance(inim, np.ndarray), "Incorrect input type!"
        height, width, channel = inim.shape
        bytesPerLine = 3 * width
        qImg = QPixmap(QImage(inim, width, height, bytesPerLine, QImage.Format_RGB888))
        return qImg
