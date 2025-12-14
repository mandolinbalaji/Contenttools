#!/usr/bin/env python3
"""
PDF/Image Extractor - Slice PDFs and images into line-by-line notation PNGs
A tool for extracting rectangular regions from PDFs and images, organizing them as draggable lines,
and exporting as PNG files for use in notation editors.

Features:
- Load PDFs (multi-page) or images
- Free-form rectangle selection
- Draggable line list (like lyrics processing)
- Export selections as PNG files
- Support for text files (display as editable text)
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image
import tempfile

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsItem, QFileDialog, QMessageBox, QTextEdit,
    QGroupBox, QComboBox, QSpinBox, QCheckBox, QProgressBar
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QImage, QIcon


class SelectionItem:
    """Represents a selected rectangle with associated data."""
    def __init__(self, rect: QRectF, page_num: int = 0, image_data: Optional[QImage] = None):
        self.rect = rect
        self.page_num = page_num
        self.image_data = image_data


class DraggableListWidget(QListWidget):
    """List widget that allows dragging items to reorder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)


class PDFImageViewer(QGraphicsView):
    """Graphics view for displaying PDFs and images with selection capability."""

    selection_changed = pyqtSignal(QRectF)
    selection_updated = pyqtSignal(QRectF)  # new_rect

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Set cross hair cursor for selection
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Selection rectangle
        self.selection_rect = None
        self.selection_start = None
        self.is_selecting = False
        self.resize_handles = []  # List of resize handle items
        self.dragging_handle = None  # Currently dragged handle
        self.handle_size = 12  # Size of resize handles (increased from 8)

    def set_image(self, pixmap: QPixmap):
        """Set the image to display."""
        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)
        self.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = 1.0
        # Clear selection and handles
        self.selection_rect = None
        self.resize_handles.clear()

    def create_resize_handles(self):
        """Create resize handles for the selection rectangle."""
        # Remove existing handles
        for handle in self.resize_handles:
            if handle in self.scene.items():
                self.scene.removeItem(handle)
        self.resize_handles.clear()

        if not self.selection_rect:
            return

        rect = self.selection_rect.rect()
        handle_positions = [
            rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight(),
            QPointF(rect.center().x(), rect.top()),  # Top center
            QPointF(rect.center().x(), rect.bottom()),  # Bottom center
            QPointF(rect.left(), rect.center().y()),  # Left center
            QPointF(rect.right(), rect.center().y()),  # Right center
        ]

        for pos in handle_positions:
            handle = QGraphicsRectItem(pos.x() - self.handle_size/2, pos.y() - self.handle_size/2,
                                     self.handle_size, self.handle_size)
            handle.setPen(QPen(QColor(255, 0, 0), 2))  # Thicker border
            handle.setBrush(QBrush(QColor(255, 255, 255, 200)))  # Semi-transparent white
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
            handle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            self.scene.addItem(handle)
            self.resize_handles.append(handle)

    def update_resize_handles(self):
        """Update positions of resize handles based on selection rectangle."""
        if not self.selection_rect or not self.resize_handles:
            return

        rect = self.selection_rect.rect()
        handle_positions = [
            rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight(),
            QPointF(rect.center().x(), rect.top()),  # Top center
            QPointF(rect.center().x(), rect.bottom()),  # Bottom center
            QPointF(rect.left(), rect.center().y()),  # Left center
            QPointF(rect.right(), rect.center().y()),  # Right center
        ]

        for i, pos in enumerate(handle_positions):
            if i < len(self.resize_handles):
                handle = self.resize_handles[i]
                handle.setRect(pos.x() - self.handle_size/2, pos.y() - self.handle_size/2,
                             self.handle_size, self.handle_size)

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming."""
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)
        self.zoom_factor *= zoom_factor

    def mousePressEvent(self, event):
        """Handle mouse press for selection start."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            # Check if clicking on a resize handle
            for i, handle in enumerate(self.resize_handles):
                if handle.contains(scene_pos):
                    self.dragging_handle = (i, scene_pos)  # Store handle index and current mouse position
                    self.original_rect = self.selection_rect.rect() if self.selection_rect else None
                    self.setDragMode(QGraphicsView.DragMode.NoDrag)
                    return
            
            # Check if clicking on existing selection rectangle
            if self.selection_rect and self.selection_rect.contains(scene_pos):
                # Don't start new selection, just allow interaction with existing
                return
            
            # Start new selection
            self.selection_start = scene_pos
            self.is_selecting = True
            # Disable drag mode during selection
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            if self.selection_rect:
                self.scene.removeItem(self.selection_rect)
                # Remove existing handles
                for handle in self.resize_handles:
                    if handle in self.scene.items():
                        self.scene.removeItem(handle)
                self.resize_handles.clear()
            self.selection_rect = QGraphicsRectItem()
            self.selection_rect.setPen(QPen(QColor(255, 0, 0), 2))
            self.selection_rect.setBrush(QBrush(QColor(255, 0, 0, 50)))
            self.scene.addItem(self.selection_rect)
            # Don't call super() to prevent default drag behavior
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for selection rectangle update."""
        scene_pos = self.mapToScene(event.pos())
        
        if self.dragging_handle is not None:
            # Dragging a resize handle
            handle_index, start_pos = self.dragging_handle
            delta = scene_pos - start_pos
            
            if self.selection_rect and self.original_rect:
                new_rect = QRectF(self.original_rect)
                
                if handle_index == 0:  # Top-left
                    new_rect.setTopLeft(self.original_rect.topLeft() + delta)
                elif handle_index == 1:  # Top-right
                    new_rect.setTopRight(self.original_rect.topRight() + delta)
                elif handle_index == 2:  # Bottom-left
                    new_rect.setBottomLeft(self.original_rect.bottomLeft() + delta)
                elif handle_index == 3:  # Bottom-right
                    new_rect.setBottomRight(self.original_rect.bottomRight() + delta)
                elif handle_index == 4:  # Top-center
                    new_rect.setTop(self.original_rect.top() + delta.y())
                elif handle_index == 5:  # Bottom-center
                    new_rect.setBottom(self.original_rect.bottom() + delta.y())
                elif handle_index == 6:  # Left-center
                    new_rect.setLeft(self.original_rect.left() + delta.x())
                elif handle_index == 7:  # Right-center
                    new_rect.setRight(self.original_rect.right() + delta.x())
                
                # Ensure minimum size
                if new_rect.width() < 10:
                    if handle_index in [0, 2, 6]:  # Left handles
                        new_rect.setLeft(new_rect.right() - 10)
                    else:  # Right handles
                        new_rect.setRight(new_rect.left() + 10)
                        
                if new_rect.height() < 10:
                    if handle_index in [0, 1, 4]:  # Top handles
                        new_rect.setTop(new_rect.bottom() - 10)
                    else:  # Bottom handles
                        new_rect.setBottom(new_rect.top() + 10)
                
                self.selection_rect.setRect(new_rect)
                self.update_resize_handles()
            return
        
        if self.is_selecting and self.selection_start:
            current_pos = scene_pos
            rect = QRectF(self.selection_start, current_pos).normalized()
            self.selection_rect.setRect(rect)
            # Don't call super() during selection to prevent panning
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release for selection completion."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging_handle is not None:
                # Finished dragging handle - emit update signal
                self.dragging_handle = None
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                if self.selection_rect:
                    # Emit update signal for the current selection
                    rect = self.selection_rect.rect()
                    self.selection_updated.emit(rect)
                return
            
            if self.is_selecting:
                self.is_selecting = False
                # Restore drag mode after selection
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                if self.selection_rect:
                    rect = self.selection_rect.rect()
                    if rect.width() > 10 and rect.height() > 10:  # Minimum size
                        # Create resize handles for the new selection
                        self.create_resize_handles()
                        self.selection_changed.emit(rect)
                    else:
                        self.scene.removeItem(self.selection_rect)
                        self.selection_rect = None
                # Don't call super() for left button during selection
                return
        super().mouseReleaseEvent(event)


class PDFImageExtractor(QMainWindow):
    """Main window for PDF/Image extraction tool."""

    def __init__(self):
        super().__init__()
        self.current_file = None
        self.current_page = 0
        self.total_pages = 0
        self.doc = None
        self.selections: List[SelectionItem] = []

        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("PDF/Image Extractor - Line-by-Line Notation PNG Slicer")
        self.setMinimumSize(1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Top toolbar
        toolbar = QHBoxLayout()

        self.load_btn = QPushButton("📂 Load PDF/Image/Text")
        self.load_btn.clicked.connect(self.load_file)

        self.prev_page_btn = QPushButton("⬅ Previous Page")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.prev_page_btn.setEnabled(False)

        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.setValue(1)
        self.page_spin.valueChanged.connect(self.go_to_page)

        self.next_page_btn = QPushButton("Next Page ➡")
        self.next_page_btn.clicked.connect(self.next_page)
        self.next_page_btn.setEnabled(False)

        self.page_label = QLabel("Page 1 of 1")

        toolbar.addWidget(self.load_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.prev_page_btn)
        toolbar.addWidget(self.page_spin)
        toolbar.addWidget(self.page_label)
        toolbar.addWidget(self.next_page_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Viewer
        viewer_group = QGroupBox("Document Viewer")
        viewer_layout = QVBoxLayout(viewer_group)

        self.viewer = PDFImageViewer()
        viewer_layout.addWidget(self.viewer)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn = QPushButton("🔍-")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.fit_btn = QPushButton("🔄 Fit")
        self.fit_btn.clicked.connect(self.fit_to_view)

        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.fit_btn)
        zoom_layout.addStretch()

        viewer_layout.addLayout(zoom_layout)

        splitter.addWidget(viewer_group)

        # Right side - Selections and export
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Selections list
        selections_group = QGroupBox("Selected Lines (Drag to reorder)")
        selections_layout = QVBoxLayout(selections_group)

        self.selections_list = DraggableListWidget()
        self.selections_list.setMaximumHeight(400)  # Increased height for thumbnails
        self.selections_list.setIconSize(QSize(100, 60))  # Set icon size for thumbnails
        selections_layout.addWidget(self.selections_list)

        # Selection controls
        sel_controls = QHBoxLayout()
        self.clear_sel_btn = QPushButton("🗑️ Clear All")
        self.clear_sel_btn.clicked.connect(self.clear_selections)
        self.remove_sel_btn = QPushButton("❌ Remove Selected")
        self.remove_sel_btn.clicked.connect(self.remove_selected)

        sel_controls.addWidget(self.clear_sel_btn)
        sel_controls.addWidget(self.remove_sel_btn)
        selections_layout.addLayout(sel_controls)

        right_layout.addWidget(selections_group)

        # Export controls
        export_group = QGroupBox("Export Options")
        export_layout = QVBoxLayout(export_group)

        self.output_dir_edit = QTextEdit()
        self.output_dir_edit.setMaximumHeight(60)
        self.output_dir_edit.setPlaceholderText("Output directory path...")
        export_layout.addWidget(self.output_dir_edit)

        self.browse_output_btn = QPushButton("📁 Browse Output Directory")
        self.browse_output_btn.clicked.connect(self.browse_output_dir)
        export_layout.addWidget(self.browse_output_btn)

        self.export_btn = QPushButton("💾 Export as PNGs")
        self.export_btn.clicked.connect(self.export_pngs)
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)

        right_layout.addWidget(export_group)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([700, 400])

        layout.addWidget(splitter)

        # Status bar
        self.status_label = QLabel("Ready - Load a PDF, image, or text file to begin")
        layout.addWidget(self.status_label)

    def setup_connections(self):
        """Setup signal connections."""
        self.viewer.selection_changed.connect(self.on_selection_made)
        self.viewer.selection_updated.connect(self.on_selection_updated)

    def load_file(self):
        """Load a PDF, image, or text file."""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("All supported files (*.pdf *.png *.jpg *.jpeg *.bmp *.txt);;PDF files (*.pdf);;Images (*.png *.jpg *.jpeg *.bmp);;Text files (*.txt)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            self.load_document(file_path)

    def load_document(self, file_path: str):
        """Load the document based on file type."""
        self.current_file = Path(file_path)
        file_ext = self.current_file.suffix.lower()

        try:
            if file_ext == '.pdf':
                self.load_pdf(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                self.load_image(file_path)
            elif file_ext == '.txt':
                self.load_text(file_path)
            else:
                QMessageBox.warning(self, "Unsupported Format", f"File type {file_ext} is not supported.")
                return

            self.status_label.setText(f"Loaded: {self.current_file.name}")
            self.export_btn.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load file: {str(e)}")

    def load_pdf(self, file_path: str):
        """Load a PDF document."""
        self.doc = fitz.open(file_path)
        self.total_pages = len(self.doc)
        self.current_page = 0
        self.update_page_display()

        # Load first page
        self.load_pdf_page(0)

    def load_pdf_page(self, page_num: int):
        """Load a specific PDF page."""
        if not self.doc or page_num >= self.total_pages:
            return

        page = self.doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scaling for better quality
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        qt_img = QImage(img.tobytes(), img.width, img.height, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)

        self.viewer.set_image(pixmap)
        self.current_page = page_num
        self.update_page_controls()

    def load_image(self, file_path: str):
        """Load an image file."""
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            raise ValueError("Failed to load image")

        self.viewer.set_image(pixmap)
        self.doc = None
        self.total_pages = 1
        self.current_page = 0
        self.update_page_display()
        self.update_page_controls()

    def load_text(self, file_path: str):
        """Load a text file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            text_content = f.read()

        # For text files, we'll create a simple text display
        # This is a placeholder - you might want to implement text rendering
        QMessageBox.information(self, "Text File", "Text file loaded. Text display not yet implemented in viewer.")

    def update_page_display(self):
        """Update page display controls."""
        if self.total_pages > 0:
            self.page_spin.setMaximum(self.total_pages)
            self.page_spin.setValue(self.current_page + 1)
            self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        else:
            self.page_label.setText("No pages")

    def update_page_controls(self):
        """Update page navigation button states."""
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)

    def prev_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.load_pdf_page(self.current_page - 1)

    def next_page(self):
        """Go to next page."""
        if self.current_page < self.total_pages - 1:
            self.load_pdf_page(self.current_page + 1)

    def go_to_page(self, page_num: int):
        """Go to specific page."""
        self.load_pdf_page(page_num - 1)

    def zoom_in(self):
        """Zoom in."""
        self.viewer.scale(1.25, 1.25)

    def zoom_out(self):
        """Zoom out."""
        self.viewer.scale(0.8, 0.8)

    def fit_to_view(self):
        """Fit image to view."""
        if self.viewer.pixmap_item:
            self.viewer.fitInView(self.viewer.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def on_selection_made(self, rect: QRectF):
        """Handle new selection rectangle."""
        # Extract the selected region as image
        if self.viewer.pixmap_item:
            pixmap = self.viewer.pixmap_item.pixmap()
            selected_pixmap = pixmap.copy(rect.toRect())

            # Create thumbnail (scale to fit in list)
            thumbnail = selected_pixmap.scaled(100, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            # Create selection item
            selection = SelectionItem(rect, self.current_page, selected_pixmap.toImage())

            # Add to list with thumbnail
            item_text = f"Line {len(self.selections) + 1}\nPage {self.current_page + 1}"
            list_item = QListWidgetItem()
            list_item.setIcon(QIcon(thumbnail))  # Convert QPixmap to QIcon
            list_item.setText(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, selection)
            self.selections_list.addItem(list_item)

            self.selections.append(selection)

            self.status_label.setText(f"Added selection: Line {len(self.selections)}")

    def on_selection_updated(self, new_rect: QRectF):
        """Handle selection rectangle updates."""
        # For now, assume the last selection is being updated
        if self.selections:
            index = len(self.selections) - 1
            # Update the selection data
            if self.viewer.pixmap_item:
                pixmap = self.viewer.pixmap_item.pixmap()
                selected_pixmap = pixmap.copy(new_rect.toRect())
                thumbnail = selected_pixmap.scaled(100, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                
                # Update the selection item
                self.selections[index].rect = new_rect
                self.selections[index].image_data = selected_pixmap.toImage()
                
                # Update the list item
                list_item = self.selections_list.item(index)
                if list_item:
                    list_item.setIcon(QIcon(thumbnail))
                    
            self.status_label.setText(f"Updated selection: Line {index + 1}")

    def clear_selections(self):
        """Clear all selections."""
        self.selections_list.clear()
        self.selections.clear()
        self.status_label.setText("All selections cleared")

    def remove_selected(self):
        """Remove selected item from list."""
        current_item = self.selections_list.currentItem()
        if current_item:
            row = self.selections_list.row(current_item)
            self.selections_list.takeItem(row)
            del self.selections[row]
            self.status_label.setText("Selection removed")

    def browse_output_dir(self):
        """Browse for output directory."""
        dir_dialog = QFileDialog()
        dir_dialog.setFileMode(QFileDialog.FileMode.Directory)

        if dir_dialog.exec():
            output_dir = dir_dialog.selectedFiles()[0]
            self.output_dir_edit.setPlainText(output_dir)

    def export_pngs(self):
        """Export all selections as PNG files."""
        output_dir_text = self.output_dir_edit.toPlainText().strip()
        if not output_dir_text:
            QMessageBox.warning(self, "No Output Directory", "Please specify an output directory.")
            return

        output_dir = Path(output_dir_text)
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True)
            except Exception as e:
                QMessageBox.critical(self, "Directory Error", f"Failed to create output directory: {str(e)}")
                return

        if not self.selections:
            QMessageBox.warning(self, "No Selections", "No selections to export.")
            return

        try:
            for i, selection in enumerate(self.selections):
                if selection.image_data:
                    filename = f"line_{i+1:03d}.png"
                    filepath = output_dir / filename
                    selection.image_data.save(str(filepath))
                    self.status_label.setText(f"Exported {filename}")

            QMessageBox.information(self, "Export Complete", f"Exported {len(self.selections)} PNG files to {output_dir}")
            self.status_label.setText(f"Export complete: {len(self.selections)} files")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export files: {str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = PDFImageExtractor()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()