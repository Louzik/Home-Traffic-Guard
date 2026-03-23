"""Главное окно приложения."""

from __future__ import annotations

import logging
import re
from ipaddress import ip_address
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QSplitter,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from home_traffic_guard.domain.models import Device
from home_traffic_guard.services.monitoring_service import AlertTableRow, DeviceTableRow, MonitoringService

INTERVAL_OPTIONS: list[tuple[str, int]] = [
    ("5 сек", 5_000),
    ("15 сек", 15_000),
    ("30 сек", 30_000),
    ("1 минута", 60_000),
    ("3 минуты", 180_000),
    ("5 минут", 300_000),
    ("10 минут", 600_000),
    ("15 минут", 900_000),
    ("30 минут", 1_800_000),
    ("1 час", 3_600_000),
    ("2 часа", 7_200_000),
    ("3 часа", 10_800_000),
    ("12 часов", 43_200_000),
    ("Раз в сутки", 86_400_000),
]

BASELINE_OPTIONS: list[float] = [1.5, 2.0, 2.5, 3.0, 4.0]
ROTATION_OPTIONS: list[tuple[str, bool]] = [("ВКЛ.", True), ("ВЫКЛ.", False)]
PROFILE_OPTIONS: list[str] = ["Локальный", "SNMP", "NetFlow", "Гибридный"]
DEFAULT_ROTATING_LOG_MAX_BYTES = 1_000_000
MAC_ADDRESS_RE = re.compile(r"^[0-9A-Fa-f]{2}([-:][0-9A-Fa-f]{2}){5}$")


class MetricCard(QFrame):
    """Декоративная карточка с метрикой раздела."""

    def __init__(self, title: str, value: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("MetricTitle")

        self._value_label = QLabel(value)
        self._value_label.setObjectName("MetricValue")

        self._caption_label = QLabel(caption)
        self._caption_label.setObjectName("MetricCaption")
        self._caption_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(self._value_label)
        layout.addWidget(self._caption_label)

    def set_value(self, value: str) -> None:
        """Обновить отображаемое значение метрики."""
        self._value_label.setText(value)

    def set_caption(self, caption: str) -> None:
        """Обновить подпись метрики."""
        self._caption_label.setText(caption)


class IntervalControlCard(QFrame):
    """Карточка интервала с кнопками переключения слева и справа."""

    def __init__(self, title: str, value: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("MetricTitle")

        controls_row = QFrame(self)
        controls_row.setObjectName("IntervalControlsRow")
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self.left_button = QPushButton("◀", self)
        self.left_button.setObjectName("IntervalStepButton")

        self._value_label = QLabel(value, self)
        self._value_label.setObjectName("IntervalValueLabel")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setMinimumWidth(120)

        self.right_button = QPushButton("▶", self)
        self.right_button.setObjectName("IntervalStepButton")

        controls_layout.addWidget(self.left_button)
        controls_layout.addWidget(self._value_label, 1)
        controls_layout.addWidget(self.right_button)

        caption_label = QLabel(caption, self)
        caption_label.setObjectName("MetricCaption")
        caption_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(controls_row, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(caption_label)

    def set_value(self, value: str) -> None:
        """Обновить значение интервала."""
        self._value_label.setText(value)

    def set_step_enabled(self, can_step_left: bool, can_step_right: bool) -> None:
        """Включить или выключить кнопки переключения."""
        self.left_button.setEnabled(can_step_left)
        self.right_button.setEnabled(can_step_right)


class PageWidget(QWidget):
    """Простой контейнер страницы с заголовком и описанием."""

    def __init__(
        self,
        title: str,
        description: str,
        metrics: list[tuple[str, str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cards: dict[str, MetricCard] = {}
        self.setObjectName("PageRoot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QFrame(self)
        header.setObjectName("HeroPanel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)

        section_label = QLabel("Раздел")
        section_label.setObjectName("SectionLabel")

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setObjectName("PageDescription")

        header_layout.addWidget(section_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(description_label)

        cards = QFrame(self)
        cards.setObjectName("CardsPanel")
        cards_layout = QGridLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(12)

        for index, metric in enumerate(metrics):
            row = index // 2
            column = index % 2
            card = MetricCard(metric[0], metric[1], metric[2], cards)
            self._cards[metric[0]] = card
            cards_layout.addWidget(
                card,
                row,
                column,
            )

        layout.addWidget(header)
        layout.addWidget(cards)
        layout.addStretch(1)

    def set_metric_value(self, title: str, value: str, caption: str | None = None) -> None:
        """Обновить значение карточки по заголовку."""
        card = self._cards.get(title)
        if card is None:
            return
        card.set_value(value)
        if caption is not None:
            card.set_caption(caption)


class DevicesPage(QWidget):
    """Страница устройств с карточками и таблицей в нижней области."""

    def __init__(
        self,
        title: str,
        description: str,
        metrics: list[tuple[str, str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cards: dict[str, MetricCard] = {}
        self.setObjectName("PageRoot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QFrame(self)
        header.setObjectName("HeroPanel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)

        section_label = QLabel("Раздел")
        section_label.setObjectName("SectionLabel")

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setObjectName("PageDescription")

        header_layout.addWidget(section_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(description_label)

        cards = QFrame(self)
        cards.setObjectName("CardsPanel")
        cards_layout = QGridLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(12)

        for index, metric in enumerate(metrics):
            row = 0
            column = index
            card = MetricCard(metric[0], metric[1], metric[2], cards)
            self._cards[metric[0]] = card
            cards_layout.addWidget(card, row, column)

        table_panel = QFrame(self)
        table_panel.setObjectName("DevicesTablePanel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(14, 12, 14, 12)
        table_layout.setSpacing(8)

        table_title = QLabel("Список устройств", table_panel)
        table_title.setObjectName("DevicesTableTitle")
        table_toolbar = QHBoxLayout()
        table_toolbar.setContentsMargins(0, 0, 0, 0)
        table_toolbar.setSpacing(8)
        table_toolbar.addWidget(table_title)
        table_toolbar.addStretch(1)

        self._add_button = QPushButton("Добавить", table_panel)
        self._add_button.setObjectName("DeviceActionButton")
        self._edit_button = QPushButton("Изменить", table_panel)
        self._edit_button.setObjectName("DeviceActionButton")
        self._delete_button = QPushButton("Удалить", table_panel)
        self._delete_button.setObjectName("DeviceDangerButton")
        self._edit_button.setEnabled(False)
        self._delete_button.setEnabled(False)

        table_toolbar.addWidget(self._add_button)
        table_toolbar.addWidget(self._edit_button)
        table_toolbar.addWidget(self._delete_button)
        table_layout.addLayout(table_toolbar)

        self._empty_state_label = QLabel(table_panel)
        self._empty_state_label.setObjectName("TableEmptyState")
        self._empty_state_label.setWordWrap(True)
        self._empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_state_label.setText(
            "Устройства пока не добавлены.\n"
            "Запустите demo mode или добавьте устройства вручную в следующем этапе."
        )
        self._empty_state_label.hide()
        table_layout.addWidget(self._empty_state_label)

        self._table = QTableWidget(table_panel)
        self._table.setObjectName("DevicesTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "Устройство", "IP", "MAC", "Скорость", "Риск", "Обновлено"]
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(False)
        self._table.setMinimumHeight(290)
        self._table.itemSelectionChanged.connect(self._sync_action_buttons)

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        table_layout.addWidget(self._table)

        layout.addWidget(header)
        layout.addWidget(cards)
        layout.addWidget(table_panel, 1)

    def set_metric_value(self, title: str, value: str, caption: str | None = None) -> None:
        """Обновить значение карточки по заголовку."""
        card = self._cards.get(title)
        if card is None:
            return
        card.set_value(value)
        if caption is not None:
            card.set_caption(caption)

    def set_rows(self, rows: list[DeviceTableRow]) -> None:
        """Заполнить таблицу устройств данными."""
        has_rows = bool(rows)
        self._table.setVisible(has_rows)
        self._empty_state_label.setVisible(not has_rows)
        self._table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self._set_item(row_index, 0, str(row.device_id), Qt.AlignmentFlag.AlignCenter)
            self._set_item(row_index, 1, row.name)
            self._set_item(row_index, 2, row.ip_address, Qt.AlignmentFlag.AlignCenter)
            self._set_item(row_index, 3, row.mac_address or "—", Qt.AlignmentFlag.AlignCenter)
            self._set_item(row_index, 4, self._format_speed(row.latest_speed_bps), Qt.AlignmentFlag.AlignCenter)
            risk_item = self._set_item(row_index, 5, row.risk_level, Qt.AlignmentFlag.AlignCenter)
            if row.risk_level == "Высокий":
                risk_item.setForeground(Qt.GlobalColor.darkRed)
            elif row.risk_level == "Низкий":
                risk_item.setForeground(Qt.GlobalColor.darkGreen)
            self._set_item(row_index, 6, self._format_updated_at(row.updated_at), Qt.AlignmentFlag.AlignCenter)
        self._sync_action_buttons()

    @property
    def add_button(self) -> QPushButton:
        """Кнопка добавления устройства."""
        return self._add_button

    @property
    def edit_button(self) -> QPushButton:
        """Кнопка редактирования устройства."""
        return self._edit_button

    @property
    def delete_button(self) -> QPushButton:
        """Кнопка удаления устройства."""
        return self._delete_button

    def selected_device_id(self) -> int | None:
        """Вернуть id выбранного устройства."""
        selected_items = self._table.selectedItems()
        if not selected_items:
            return None
        row = selected_items[0].row()
        id_item = self._table.item(row, 0)
        if id_item is None:
            return None
        try:
            return int(id_item.text())
        except ValueError:
            return None

    def _sync_action_buttons(self) -> None:
        has_selection = self.selected_device_id() is not None
        self._edit_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)

    def _set_item(
        self,
        row: int,
        column: int,
        text: str,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(int(alignment))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, column, item)
        return item

    @staticmethod
    def _format_speed(bytes_per_second: float) -> str:
        if bytes_per_second < 1024:
            return f"{bytes_per_second:.0f} Б/с"
        if bytes_per_second < 1024 * 1024:
            return f"{bytes_per_second / 1024:.1f} КБ/с"
        return f"{bytes_per_second / (1024 * 1024):.2f} МБ/с"

    @staticmethod
    def _format_updated_at(updated_at: datetime | None) -> str:
        if updated_at is None:
            return "—"
        return updated_at.strftime("%d.%m %H:%M:%S")


class AlertsPage(QWidget):
    """Страница оповещений с карточками, фильтрами и таблицей."""

    _MESSAGE_PREVIEW_LENGTH = 90

    def __init__(
        self,
        title: str,
        description: str,
        metrics: list[tuple[str, str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cards: dict[str, MetricCard] = {}
        self._expanded_alert_ids: set[int] = set()
        self.setObjectName("PageRoot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QFrame(self)
        header.setObjectName("HeroPanel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)

        section_label = QLabel("Раздел")
        section_label.setObjectName("SectionLabel")

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")

        description_label = QLabel(description)
        description_label.setWordWrap(True)
        description_label.setObjectName("PageDescription")

        header_layout.addWidget(section_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(description_label)

        cards = QFrame(self)
        cards.setObjectName("CardsPanel")
        cards_layout = QGridLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(12)

        for index, metric in enumerate(metrics):
            row = index // 2
            column = index % 2
            card = MetricCard(metric[0], metric[1], metric[2], cards)
            self._cards[metric[0]] = card
            cards_layout.addWidget(card, row, column)

        table_panel = QFrame(self)
        table_panel.setObjectName("AlertsTablePanel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(14, 12, 14, 12)
        table_layout.setSpacing(8)

        controls_frame = QFrame(table_panel)
        controls_frame.setObjectName("AlertsToolbar")
        controls = QHBoxLayout(controls_frame)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(10)

        severity_filter_frame = QFrame(table_panel)
        severity_filter_frame.setObjectName("AlertsFilterGroup")
        severity_filter_frame.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        severity_filter_frame.setFixedHeight(38)
        severity_layout = QHBoxLayout(severity_filter_frame)
        severity_layout.setContentsMargins(0, 0, 0, 0)
        severity_layout.setSpacing(8)

        self._severity_filter_group = QButtonGroup(self)
        self._severity_filter_group.setExclusive(True)
        self._severity_buttons: list[QPushButton] = []

        for text, severity_value in [
            ("Все уровни", None),
            ("Критичные", "high"),
            ("Средние", "medium"),
            ("Низкие", "low"),
        ]:
            button = QPushButton(text, severity_filter_frame)
            button.setObjectName("AlertsFilterButton")
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setAutoDefault(False)
            button.setDefault(False)
            button.setProperty("severity", severity_value if severity_value is not None else "")
            button.setProperty("filterRole", severity_value if severity_value is not None else "all")
            button.setFixedHeight(36)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            text_width = button.fontMetrics().horizontalAdvance(text)
            button.setMinimumWidth(text_width + 46)
            self._severity_filter_group.addButton(button)
            self._severity_buttons.append(button)
            severity_layout.addWidget(button)

        self._severity_buttons[0].setChecked(True)

        self._unack_only_checkbox = QCheckBox("Только неподтвержденные", table_panel)
        self._unack_only_checkbox.setObjectName("AlertsUnackOnly")

        self._ack_button = QPushButton("Подтвердить", table_panel)
        self._ack_button.setObjectName("AlertsAckButton")
        self._ack_button.setEnabled(False)
        ack_text_width = self._ack_button.fontMetrics().horizontalAdvance("Снять подтверждение")
        self._ack_button.setMinimumWidth(ack_text_width + 30)
        self._ack_button.setFixedHeight(38)
        self._ack_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        controls.addWidget(severity_filter_frame, 0, Qt.AlignmentFlag.AlignVCenter)
        controls.addWidget(self._unack_only_checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
        controls.addStretch(1)
        controls.addWidget(self._ack_button, 0, Qt.AlignmentFlag.AlignVCenter)
        table_layout.addWidget(controls_frame)

        self._empty_state_label = QLabel(table_panel)
        self._empty_state_label.setObjectName("TableEmptyState")
        self._empty_state_label.setWordWrap(True)
        self._empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_state_label.hide()
        table_layout.addWidget(self._empty_state_label)

        self._table = QTableWidget(table_panel)
        self._table.setObjectName("AlertsTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["", "Время", "Устройство", "Уровень", "Сообщение", "Статус", "Подтверждено"]
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(False)
        self._table.setMinimumHeight(290)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        header_view = self._table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 40)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        table_layout.addWidget(self._table)
        split = QSplitter(Qt.Orientation.Vertical, self)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)
        split.addWidget(cards)
        split.addWidget(table_panel)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([150, 850])

        layout.addWidget(header)
        layout.addWidget(split, 1)

    @property
    def severity_filter_buttons(self) -> tuple[QPushButton, ...]:
        """Кнопки фильтрации по уровню риска."""
        return tuple(self._severity_buttons)

    @property
    def unack_only_checkbox(self) -> QCheckBox:
        """Чекбокс для показа только неподтвержденных оповещений."""
        return self._unack_only_checkbox

    @property
    def ack_button(self) -> QPushButton:
        """Кнопка подтверждения/снятия подтверждения оповещения."""
        return self._ack_button

    def selected_severity_filter(self) -> str | None:
        """Вернуть выбранный фильтр уровня."""
        selected_button = self._severity_filter_group.checkedButton()
        if selected_button is None:
            return None
        value = selected_button.property("severity")
        if value in (None, ""):
            return None
        return str(value)

    def only_unacknowledged(self) -> bool:
        """Проверить, включен ли фильтр неподтвержденных оповещений."""
        return self._unack_only_checkbox.isChecked()

    def checked_alerts(self) -> list[tuple[int, bool]]:
        """Вернуть выбранные оповещения: (id, acknowledged)."""
        result: list[tuple[int, bool]] = []
        for row in range(self._table.rowCount()):
            checkbox = self._checkbox_for_row(row)
            status_item = self._table.item(row, 5)
            if checkbox is None or status_item is None:
                continue
            if not checkbox.isChecked():
                continue
            alert_id = checkbox.property("alertId")
            if not isinstance(alert_id, int):
                continue
            acknowledged = bool(status_item.data(Qt.ItemDataRole.UserRole))
            result.append((alert_id, acknowledged))
        return result

    def set_metric_value(self, title: str, value: str, caption: str | None = None) -> None:
        """Обновить значение карточки по заголовку."""
        card = self._cards.get(title)
        if card is None:
            return
        card.set_value(value)
        if caption is not None:
            card.set_caption(caption)

    def set_rows(self, rows: list[AlertTableRow]) -> None:
        """Заполнить таблицу оповещений."""
        has_rows = bool(rows)
        self._table.setVisible(has_rows)
        self._empty_state_label.setVisible(not has_rows)
        checked_ids: set[int] = set()
        for row in range(self._table.rowCount()):
            checkbox = self._checkbox_for_row(row)
            if checkbox is None:
                continue
            if not checkbox.isChecked():
                continue
            alert_id = checkbox.property("alertId")
            if isinstance(alert_id, int):
                checked_ids.add(alert_id)

        self._table.blockSignals(True)
        self._table.setUpdatesEnabled(False)
        try:
            self._table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                select_widget = QWidget(self._table)
                select_layout = QHBoxLayout(select_widget)
                # Легкий сдвиг влево для визуального центрирования в узкой колонке.
                select_layout.setContentsMargins(0, 0, 6, 0)
                select_layout.setSpacing(0)
                select_checkbox = QCheckBox(select_widget)
                select_checkbox.setObjectName("AlertsSelectCheckbox")
                select_checkbox.setChecked(row.alert_id in checked_ids)
                select_checkbox.setProperty("alertId", row.alert_id)
                select_checkbox.stateChanged.connect(lambda _: self._sync_ack_button_state())
                select_layout.addStretch(1)
                select_layout.addWidget(select_checkbox)
                select_layout.addStretch(1)
                self._table.setCellWidget(row_index, 0, select_widget)
                self._set_item(
                    row_index,
                    1,
                    row.created_at.strftime("%d.%m %H:%M:%S"),
                    Qt.AlignmentFlag.AlignCenter,
                )
                self._set_item(row_index, 2, row.device_name)
                severity_text = self._severity_to_text(row.severity)
                severity_item = self._set_item(row_index, 3, severity_text, Qt.AlignmentFlag.AlignCenter)
                if row.severity.lower() == "high":
                    severity_item.setForeground(Qt.GlobalColor.darkRed)
                elif row.severity.lower() == "medium":
                    severity_item.setForeground(Qt.GlobalColor.darkYellow)
                else:
                    severity_item.setForeground(Qt.GlobalColor.darkGreen)
                self._table.setCellWidget(
                    row_index,
                    4,
                    self._build_message_cell(row_index, row.alert_id, row.message),
                )
                status_item = self._set_item(
                    row_index,
                    5,
                    "Подтверждено" if row.acknowledged else "Новое",
                    Qt.AlignmentFlag.AlignCenter,
                )
                status_item.setData(Qt.ItemDataRole.UserRole, row.acknowledged)
                if row.acknowledged:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                self._set_item(
                    row_index,
                    6,
                    row.acknowledged_at.strftime("%d.%m %H:%M:%S") if row.acknowledged_at else "—",
                    Qt.AlignmentFlag.AlignCenter,
                )
                self._apply_row_height(row_index, row.alert_id)
        finally:
            self._table.setUpdatesEnabled(True)
            self._table.blockSignals(False)

        self._sync_ack_button_state()

    def set_empty_state_message(self, message: str) -> None:
        """Обновить сообщение пустого состояния таблицы оповещений."""
        self._empty_state_label.setText(message)

    def _checkbox_for_row(self, row: int) -> QCheckBox | None:
        widget = self._table.cellWidget(row, 0)
        if widget is None:
            return None
        return widget.findChild(QCheckBox, "AlertsSelectCheckbox")

    def _build_message_cell(self, row: int, alert_id: int, message: str) -> QWidget:
        """Собрать ячейку сообщения с inline разворачиванием текста."""
        container = QWidget(self._table)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        label = QLabel(container)
        label.setToolTip(message)
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        label.setWordWrap(True)
        label.setStyleSheet("color: #1e3d4f; font-size: 11px; font-weight: 400;")

        expand_button = QPushButton("⋯", container)
        expand_button.setObjectName("AlertMessageExpandButton")
        expand_button.setFixedSize(18, 18)
        expand_button.clicked.connect(
            lambda _:
            self._toggle_message_expanded(row, alert_id, message, label, expand_button)
        )

        layout.addWidget(label, 1)
        layout.addWidget(expand_button, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self._apply_message_state(row, alert_id, message, label, expand_button)
        return container

    def _toggle_message_expanded(
        self,
        row: int,
        alert_id: int,
        message: str,
        label: QLabel,
        button: QPushButton,
    ) -> None:
        if alert_id in self._expanded_alert_ids:
            self._expanded_alert_ids.discard(alert_id)
        else:
            self._expanded_alert_ids.add(alert_id)
        self._apply_message_state(row, alert_id, message, label, button)

    def _apply_message_state(
        self,
        row: int,
        alert_id: int,
        message: str,
        label: QLabel,
        button: QPushButton,
    ) -> None:
        expanded = alert_id in self._expanded_alert_ids
        if expanded:
            label.setText(message)
            button.setText("▴")
            button.setToolTip("Свернуть сообщение")
        else:
            short = self._short_message(message)
            label.setText(short)
            button.setText("⋯")
            button.setToolTip("Развернуть сообщение")
        self._apply_row_height(row, alert_id)

    def _apply_row_height(self, row: int, alert_id: int) -> None:
        if alert_id in self._expanded_alert_ids:
            self._table.resizeRowToContents(row)
            self._table.setRowHeight(row, max(self._table.rowHeight(row), 64))
        else:
            self._table.setRowHeight(row, 42)

    def _short_message(self, message: str) -> str:
        if len(message) <= self._MESSAGE_PREVIEW_LENGTH:
            return message
        cut = self._MESSAGE_PREVIEW_LENGTH - 3
        return f"{message[:cut]}..."

    def _sync_ack_button_state(self) -> None:
        checked = self.checked_alerts()
        if not checked:
            self._ack_button.setEnabled(False)
            self._ack_button.setText("Подтвердить")
            return
        unack_count = sum(1 for _, acknowledged in checked if not acknowledged)
        self._ack_button.setEnabled(unack_count > 0)
        self._ack_button.setText(
            f"Подтвердить ({unack_count})" if unack_count > 0 else "Подтверждено"
        )

    def _set_item(
        self,
        row: int,
        column: int,
        text: str,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(int(alignment))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, column, item)
        return item

    @staticmethod
    def _severity_to_text(severity: str) -> str:
        value = severity.lower()
        if value == "high":
            return "Критичный"
        if value == "medium":
            return "Средний"
        return "Низкий"


class SettingsPage(QWidget):
    """Страница настроек с управляемыми карточками параметров мониторинга."""

    def __init__(
        self,
        current_interval_ms: int,
        current_baseline_multiplier: float,
        rotation_enabled: bool,
        profile_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._interval_values = [value for _, value in INTERVAL_OPTIONS]
        self._baseline_values = BASELINE_OPTIONS
        self._rotation_values = [value for _, value in ROTATION_OPTIONS]
        self._profile_values = PROFILE_OPTIONS

        self._interval_index = self._index_for_interval(current_interval_ms)
        self._baseline_index = self._index_for_baseline(current_baseline_multiplier)
        self._rotation_index = self._index_for_rotation(rotation_enabled)
        self._profile_index = self._index_for_profile(profile_name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        header = QFrame(self)
        header.setObjectName("HeroPanel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)

        section_label = QLabel("Раздел", header)
        section_label.setObjectName("SectionLabel")

        title_label = QLabel("Настройки", header)
        title_label.setObjectName("PageTitle")

        description_label = QLabel(
            "Параметры приложения, мониторинга и аналитических правил.",
            header,
        )
        description_label.setObjectName("PageDescription")
        description_label.setWordWrap(True)

        header_layout.addWidget(section_label)
        header_layout.addWidget(title_label)
        header_layout.addWidget(description_label)

        cards = QFrame(self)
        cards.setObjectName("CardsPanel")
        cards_layout = QGridLayout(cards)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(12)
        cards_layout.setVerticalSpacing(12)

        self._interval_metric = IntervalControlCard(
            "Интервал опроса",
            self.selected_interval_label(),
            "Частота запуска цикла сбора данных.",
            cards,
        )
        self._baseline_metric = IntervalControlCard(
            "Порог baseline",
            self.selected_baseline_label(),
            "Множитель, задающий границу аномалии.",
            cards,
        )
        self._rotation_metric = IntervalControlCard(
            "Ротация логов",
            self.selected_rotation_label(),
            "Автоматическое ограничение размера файлов логирования.",
            cards,
        )
        self._profile_metric = IntervalControlCard(
            "Профиль",
            self.selected_profile_name(),
            "Текущая конфигурация мониторинга и интеграций.",
            cards,
        )

        cards_layout.addWidget(self._interval_metric, 0, 0)
        cards_layout.addWidget(self._baseline_metric, 0, 1)
        cards_layout.addWidget(self._rotation_metric, 1, 0)
        cards_layout.addWidget(self._profile_metric, 1, 1)

        layout.addWidget(header)
        layout.addWidget(cards)
        layout.addStretch(1)

        self._update_all_controls()

    @property
    def interval_left_button(self) -> QPushButton:
        """Кнопка уменьшения интервала."""
        return self._interval_metric.left_button

    @property
    def interval_right_button(self) -> QPushButton:
        """Кнопка увеличения интервала."""
        return self._interval_metric.right_button

    @property
    def baseline_left_button(self) -> QPushButton:
        """Кнопка уменьшения baseline."""
        return self._baseline_metric.left_button

    @property
    def baseline_right_button(self) -> QPushButton:
        """Кнопка увеличения baseline."""
        return self._baseline_metric.right_button

    @property
    def rotation_left_button(self) -> QPushButton:
        """Кнопка изменения состояния ротации влево."""
        return self._rotation_metric.left_button

    @property
    def rotation_right_button(self) -> QPushButton:
        """Кнопка изменения состояния ротации вправо."""
        return self._rotation_metric.right_button

    @property
    def profile_left_button(self) -> QPushButton:
        """Кнопка переключения профиля влево."""
        return self._profile_metric.left_button

    @property
    def profile_right_button(self) -> QPushButton:
        """Кнопка переключения профиля вправо."""
        return self._profile_metric.right_button

    def selected_interval_ms(self) -> int:
        """Вернуть выбранный интервал в миллисекундах."""
        return self._interval_values[self._interval_index]

    def selected_interval_label(self) -> str:
        """Вернуть текст выбранного интервала."""
        return self._label_for_interval(self.selected_interval_ms())

    def selected_baseline_multiplier(self) -> float:
        """Вернуть выбранный множитель baseline."""
        return self._baseline_values[self._baseline_index]

    def selected_baseline_label(self) -> str:
        """Вернуть текст выбранного множителя baseline."""
        return f"x{self.selected_baseline_multiplier():.1f}"

    def selected_rotation_enabled(self) -> bool:
        """Вернуть флаг ротации логов."""
        return self._rotation_values[self._rotation_index]

    def selected_rotation_label(self) -> str:
        """Вернуть текст состояния ротации."""
        return "ВКЛ." if self.selected_rotation_enabled() else "ВЫКЛ."

    def selected_profile_name(self) -> str:
        """Вернуть имя выбранного профиля."""
        return self._profile_values[self._profile_index]

    def step_interval(self, direction: int) -> int:
        """Сместить интервал на один шаг влево/вправо и вернуть новое значение."""
        self._interval_index = self._step_index(self._interval_index, len(self._interval_values), direction)
        self._update_interval_view()
        return self.selected_interval_ms()

    def step_baseline(self, direction: int) -> float:
        """Сместить baseline на один шаг и вернуть новое значение."""
        self._baseline_index = self._step_index(self._baseline_index, len(self._baseline_values), direction)
        self._update_baseline_view()
        return self.selected_baseline_multiplier()

    def step_rotation(self, direction: int) -> bool:
        """Сместить состояние ротации на один шаг и вернуть новое значение."""
        self._rotation_index = self._step_index(self._rotation_index, len(self._rotation_values), direction)
        self._update_rotation_view()
        return self.selected_rotation_enabled()

    def step_profile(self, direction: int) -> str:
        """Сместить профиль на один шаг и вернуть новое значение."""
        self._profile_index = self._step_index(self._profile_index, len(self._profile_values), direction)
        self._update_profile_view()
        return self.selected_profile_name()

    def set_current_interval_ms(self, interval_ms: int) -> None:
        """Установить текущий интервал и обновить карточку."""
        self._interval_index = self._index_for_interval(interval_ms)
        self._update_interval_view()

    def set_current_baseline_multiplier(self, multiplier: float) -> None:
        """Установить текущий baseline и обновить карточку."""
        self._baseline_index = self._index_for_baseline(multiplier)
        self._update_baseline_view()

    def set_current_rotation_enabled(self, enabled: bool) -> None:
        """Установить состояние ротации и обновить карточку."""
        self._rotation_index = self._index_for_rotation(enabled)
        self._update_rotation_view()

    def set_current_profile(self, profile_name: str) -> None:
        """Установить профиль и обновить карточку."""
        self._profile_index = self._index_for_profile(profile_name)
        self._update_profile_view()

    def _update_all_controls(self) -> None:
        self._update_interval_view()
        self._update_baseline_view()
        self._update_rotation_view()
        self._update_profile_view()

    def _update_interval_view(self) -> None:
        self._interval_metric.set_value(self.selected_interval_label())
        self._interval_metric.set_step_enabled(
            can_step_left=len(self._interval_values) > 1,
            can_step_right=len(self._interval_values) > 1,
        )

    def _update_baseline_view(self) -> None:
        self._baseline_metric.set_value(self.selected_baseline_label())
        self._baseline_metric.set_step_enabled(
            can_step_left=len(self._baseline_values) > 1,
            can_step_right=len(self._baseline_values) > 1,
        )

    def _update_rotation_view(self) -> None:
        self._rotation_metric.set_value(self.selected_rotation_label())
        self._rotation_metric.set_step_enabled(
            can_step_left=len(self._rotation_values) > 1,
            can_step_right=len(self._rotation_values) > 1,
        )

    def _update_profile_view(self) -> None:
        self._profile_metric.set_value(self.selected_profile_name())
        self._profile_metric.set_step_enabled(
            can_step_left=len(self._profile_values) > 1,
            can_step_right=len(self._profile_values) > 1,
        )

    def _index_for_interval(self, interval_ms: int) -> int:
        for index, value in enumerate(self._interval_values):
            if value == interval_ms:
                return index
        return 1  # 15 сек по умолчанию

    def _index_for_baseline(self, multiplier: float) -> int:
        for index, value in enumerate(self._baseline_values):
            if abs(value - multiplier) < 1e-9:
                return index
        return 1  # x2.0 по умолчанию

    def _index_for_rotation(self, enabled: bool) -> int:
        for index, value in enumerate(self._rotation_values):
            if value == enabled:
                return index
        return 0

    def _index_for_profile(self, profile_name: str) -> int:
        for index, value in enumerate(self._profile_values):
            if value == profile_name:
                return index
        return 0

    @staticmethod
    def _step_index(current_index: int, total: int, direction: int) -> int:
        if direction not in (-1, 1):
            return current_index
        if total <= 0:
            return current_index
        return (current_index + direction) % total

    @staticmethod
    def _label_for_interval(interval_ms: int) -> str:
        for text, value in INTERVAL_OPTIONS:
            if value == interval_ms:
                return text
        return f"{interval_ms} мс"


class MainWindow(QMainWindow):
    """QMainWindow с левой навигацией и стеком страниц контента."""

    def __init__(self, monitoring_service: MonitoringService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._monitoring_service = monitoring_service
        self._monitoring_enabled = True
        self._settings = QSettings("HomeTrafficGuard", "HomeTrafficGuard")
        self._rotation_enabled = True
        self._profile_name = PROFILE_OPTIONS[0]
        self._apply_saved_interval()
        self._apply_saved_baseline()
        self._load_saved_rotation()
        self._load_saved_profile()
        self.setWindowTitle("Home Traffic Guard")
        self.resize(1280, 850)
        self.setMinimumSize(1280, 850)

        self.setStyleSheet(
            """
            QWidget#AppRoot {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d0d6de, stop:1 #c3cbd5);
                font-family: "SF Pro Text", "Segoe UI", "Noto Sans";
                color: #21303a;
            }
            QFrame#Sidebar {
                background-color: #183344;
                border-radius: 16px;
            }
            QLabel#BrandMark {
                color: #183344;
                background-color: #f3b75f;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 700;
                padding: 6px 8px;
            }
            QLabel#BrandTitle {
                color: #f4f9ff;
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#BrandSubtitle {
                color: #c6d8e5;
                font-size: 12px;
            }
            QListWidget#NavList {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #d8e8f4;
                outline: none;
            }
            QListWidget#NavList::item {
                padding: 12px 14px;
                border-radius: 10px;
                margin: 2px 0;
            }
            QListWidget#NavList::item:hover {
                background-color: rgba(255, 255, 255, 0.10);
            }
            QListWidget#NavList::item:selected {
                background-color: #f3b75f;
                color: #132632;
                font-weight: 700;
            }
            QFrame#StatusPanel {
                background-color: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 12px;
            }
            QLabel#StatusTitle {
                color: #f3f9ff;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton#StatusToggle {
                font-weight: 700;
                font-size: 13px;
                border: none;
                background: transparent;
                text-align: left;
                padding: 0;
            }
            QPushButton#StatusToggle[active="true"] {
                color: #9ae6b4;
            }
            QPushButton#StatusToggle[active="false"] {
                color: #ff9b9b;
            }
            QPushButton#StatusToggle[active="true"]:hover {
                color: #b7f3ca;
            }
            QPushButton#StatusToggle[active="true"]:pressed {
                color: #87d6a6;
            }
            QPushButton#StatusToggle[active="false"]:hover {
                color: #ffb3b3;
            }
            QPushButton#StatusToggle[active="false"]:pressed {
                color: #ff8686;
            }
            QFrame#ContentShell {
                background-color: rgba(191, 201, 212, 0.78);
                border: 1px solid #aab7c3;
                border-radius: 16px;
            }
            QFrame#HeroPanel {
                background-color: #c6cfd9;
                border: 1px solid #a8b5c1;
                border-radius: 14px;
            }
            QLabel#SectionLabel {
                color: #5c7687;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#PageTitle {
                color: #153447;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#PageDescription {
                color: #3f5868;
                font-size: 14px;
            }
            QFrame#MetricCard {
                background-color: #d4dbe3;
                border: 1px solid #b2bfcb;
                border-radius: 12px;
            }
            QLabel#MetricTitle {
                color: #4f6776;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#MetricValue {
                color: #1c3e52;
                font-size: 26px;
                font-weight: 700;
            }
            QLabel#MetricCaption {
                color: #617988;
                font-size: 12px;
            }
            QLabel#TableEmptyState {
                color: #4d6676;
                font-size: 13px;
                font-weight: 600;
                background-color: #dde4eb;
                border: 1px dashed #aebbc8;
                border-radius: 10px;
                padding: 20px 18px;
            }
            QFrame#IntervalControlsRow {
                max-width: 220px;
                background: transparent;
            }
            QPushButton#IntervalStepButton {
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                border: none;
                border-radius: 15px;
                background-color: transparent;
                color: #2c5367;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#IntervalStepButton:hover {
                background-color: rgba(44, 83, 103, 0.10);
            }
            QPushButton#IntervalStepButton:pressed {
                background-color: rgba(44, 83, 103, 0.16);
            }
            QPushButton#IntervalStepButton:disabled {
                color: #9db2bf;
                background-color: transparent;
            }
            QLabel#IntervalValueLabel {
                color: #1c3e52;
                font-size: 22px;
                font-weight: 700;
            }
            QFrame#DevicesTablePanel {
                background-color: #d4dbe3;
                border: 1px solid #b2bfcb;
                border-radius: 12px;
            }
            QLabel#DevicesTableTitle {
                color: #38596c;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton#DeviceActionButton {
                min-height: 34px;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                background-color: #2f5d78;
                color: #f4f9ff;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#DeviceActionButton:hover:!disabled {
                background-color: #3d7290;
            }
            QPushButton#DeviceActionButton:pressed:!disabled {
                background-color: #29566f;
            }
            QPushButton#DeviceActionButton:disabled {
                background-color: #8f9eab;
                color: #dbe3ea;
            }
            QPushButton#DeviceDangerButton {
                min-height: 34px;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                background-color: #a74c53;
                color: #fff5f5;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#DeviceDangerButton:hover:!disabled {
                background-color: #bb5d65;
            }
            QPushButton#DeviceDangerButton:pressed:!disabled {
                background-color: #913f46;
            }
            QPushButton#DeviceDangerButton:disabled {
                background-color: #9f9ea3;
                color: #e4e3e7;
            }
            QTableWidget#DevicesTable {
                background-color: #dce2e9;
                alternate-background-color: #d2d9e1;
                border: 1px solid #aebac7;
                border-radius: 8px;
                gridline-color: #b7c2ce;
                color: #1e3d4f;
                font-size: 11px;
                selection-background-color: #b7c8d6;
                selection-color: #173243;
            }
            QHeaderView::section {
                background-color: #c5cfda;
                color: #274657;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-right: 1px solid #b4bfcb;
                padding: 6px 8px;
            }
            QFrame#AlertsTablePanel {
                background-color: #d4dbe3;
                border: 1px solid #b2bfcb;
                border-radius: 12px;
            }
            QFrame#AlertsToolbar {
                background-color: #ccd5df;
                border: 1px solid #adb9c6;
                border-radius: 10px;
                padding: 8px;
            }
            QFrame#AlertsFilterGroup {
                background-color: #d8e0e8;
                border: 1px solid #a9b8c5;
                border-radius: 12px;
            }
            QPushButton#AlertsFilterButton {
                border: none;
                border-radius: 9px;
                padding: 0 14px;
                background-color: transparent;
                color: #35586d;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#AlertsFilterButton[filterRole="all"]:hover:!checked {
                background-color: rgba(61, 94, 117, 0.10);
            }
            QPushButton#AlertsFilterButton[filterRole="all"]:pressed:!checked {
                background-color: rgba(61, 94, 117, 0.15);
            }
            QPushButton#AlertsFilterButton[filterRole="all"]:checked {
                background-color: #2f5d78;
                color: #eef6ff;
            }
            QPushButton#AlertsFilterButton[filterRole="high"]:hover:!checked {
                background-color: rgba(191, 59, 70, 0.14);
                color: #8e2431;
            }
            QPushButton#AlertsFilterButton[filterRole="high"]:pressed:!checked {
                background-color: rgba(191, 59, 70, 0.22);
                color: #7e1d29;
            }
            QPushButton#AlertsFilterButton[filterRole="high"]:checked {
                background-color: #ba3844;
                color: #fff4f4;
            }
            QPushButton#AlertsFilterButton[filterRole="medium"]:hover:!checked {
                background-color: rgba(221, 168, 59, 0.18);
                color: #705218;
            }
            QPushButton#AlertsFilterButton[filterRole="medium"]:pressed:!checked {
                background-color: rgba(221, 168, 59, 0.27);
                color: #624611;
            }
            QPushButton#AlertsFilterButton[filterRole="medium"]:checked {
                background-color: #dca73b;
                color: #3f2e06;
            }
            QPushButton#AlertsFilterButton[filterRole="low"]:hover:!checked {
                background-color: rgba(69, 154, 91, 0.16);
                color: #2f6e42;
            }
            QPushButton#AlertsFilterButton[filterRole="low"]:pressed:!checked {
                background-color: rgba(69, 154, 91, 0.24);
                color: #265938;
            }
            QPushButton#AlertsFilterButton[filterRole="low"]:checked {
                background-color: #459a5b;
                color: #f1fff4;
            }
            QCheckBox#AlertsUnackOnly {
                color: #25495d;
                font-size: 12px;
                font-weight: 600;
                spacing: 8px;
            }
            QCheckBox#AlertsUnackOnly::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #8ea3b4;
                border-radius: 5px;
                background-color: #e7edf2;
            }
            QCheckBox#AlertsUnackOnly::indicator:checked {
                background-color: #2f5d78;
                border: 1px solid #2f5d78;
            }
            QCheckBox#AlertsSelectCheckbox {
                spacing: 0;
                background: transparent;
            }
            QCheckBox#AlertsSelectCheckbox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #8ea3b4;
                border-radius: 5px;
                background-color: #d7dfe8;
            }
            QCheckBox#AlertsSelectCheckbox::indicator:hover {
                border: 1px solid #6e8799;
                background-color: #e0e7ee;
            }
            QCheckBox#AlertsSelectCheckbox::indicator:checked {
                background-color: #2a5872;
                border: 1px solid #2a5872;
            }
            QPushButton#AlertMessageExpandButton {
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                border: 1px solid #8ea3b4;
                border-radius: 4px;
                background-color: #d9e0e8;
                color: #35586d;
                font-size: 11px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton#AlertMessageExpandButton:hover {
                background-color: #e2e8ee;
                border-color: #7891a2;
                color: #274657;
            }
            QPushButton#AlertMessageExpandButton:pressed {
                background-color: #cfd8e1;
                border-color: #6c8596;
            }
            QPushButton#AlertsAckButton {
                min-height: 36px;
                border: none;
                border-radius: 10px;
                padding: 0 14px;
                background-color: #2f5d78;
                color: #f4f9ff;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton#AlertsAckButton:disabled {
                background-color: #8f9eab;
                color: #dbe3ea;
            }
            QPushButton#AlertsAckButton:hover:!disabled {
                background-color: #3d7290;
            }
            QPushButton#AlertsAckButton:pressed:!disabled {
                background-color: #29566f;
            }
            QTableWidget#AlertsTable {
                background-color: #dce2e9;
                alternate-background-color: #d2d9e1;
                border: 1px solid #aebac7;
                border-radius: 8px;
                gridline-color: #b7c2ce;
                color: #1e3d4f;
                font-size: 11px;
                selection-background-color: #b7c8d6;
                selection-color: #173243;
            }
            """
        )

        root = QWidget(self)
        root.setObjectName("AppRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        sidebar = QFrame(root)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 18, 18, 18)
        sidebar_layout.setSpacing(14)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(14)
        brand_mark = QLabel("HTG", sidebar)
        brand_mark.setObjectName("BrandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedWidth(52)

        brand_texts = QVBoxLayout()
        brand_title = QLabel("Home Traffic Guard", sidebar)
        brand_title.setObjectName("BrandTitle")
        brand_title.setWordWrap(False)
        brand_title.setMinimumWidth(190)
        brand_subtitle = QLabel("Мониторинг трафика умного дома", sidebar)
        brand_subtitle.setObjectName("BrandSubtitle")
        brand_subtitle.setWordWrap(True)
        brand_texts.addWidget(brand_title)
        brand_texts.addWidget(brand_subtitle)

        brand_row.addWidget(brand_mark)
        brand_row.addLayout(brand_texts, 1)
        sidebar_layout.addLayout(brand_row)

        self._nav_list = QListWidget(sidebar)
        self._nav_list.addItems(["Обзор", "Устройства", "Оповещения", "Настройки"])
        self._nav_list.setObjectName("NavList")
        sidebar_layout.addWidget(self._nav_list, 1)

        status_panel = QFrame(sidebar)
        status_panel.setObjectName("StatusPanel")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_layout.setSpacing(2)

        status_title = QLabel("Состояние мониторинга", status_panel)
        status_title.setObjectName("StatusTitle")
        status_value = QPushButton(status_panel)
        status_value.setObjectName("StatusToggle")
        status_value.setCursor(Qt.CursorShape.PointingHandCursor)
        status_layout.addWidget(status_title)
        status_layout.addWidget(status_value)
        self._status_value_label = status_value

        sidebar_layout.addWidget(status_panel)

        content_shell = QFrame(root)
        content_shell.setObjectName("ContentShell")
        content_layout = QVBoxLayout(content_shell)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self._pages = QStackedWidget(content_shell)
        self._overview_page = PageWidget(
            "Обзор",
            "Состояние системы и сводка по трафику в реальном времени.",
            [
                ("Текущая скорость", "0 Б/с", "Суммарный входящий поток по всем устройствам."),
                ("Активные устройства", "0", "Устройства, от которых получены данные за последнюю минуту."),
                ("Аномалии за сутки", "0", "События, превысившие baseline-порог в 2 раза."),
                ("Последнее обновление", "нет данных", "Время завершения последнего цикла мониторинга."),
            ],
            self._pages,
        )
        self._pages.addWidget(self._overview_page)
        self._devices_page = DevicesPage(
            "Устройства",
            "Управляемые устройства умного дома и их сетевой профиль.",
            [
                ("Всего устройств", "0", "Зарегистрировано в локальной базе данных."),
                ("В зоне риска", "0", "Устройства с резкими всплесками трафика."),
                ("Новые за 7 дней", "0", "Недавно добавленные элементы инфраструктуры."),
                ("Покрытие мониторинга", "0%", "Доля устройств с валидным IP и историей замеров."),
            ],
            self._pages,
        )
        self._pages.addWidget(self._devices_page)
        self._alerts_page = AlertsPage(
            "Оповещения",
            "Аномалии и события безопасности, требующие внимания.",
            [
                ("Критичные", "0", "Неподтвержденные события с высоким уровнем риска."),
                ("Средние", "0", "Неподтвержденные отклонения, которые стоит перепроверить."),
                ("Низкие", "0", "Неподтвержденные информационные предупреждения."),
                ("Подтверждено", "0", "Оповещения, по которым завершена проверка."),
            ],
            self._pages,
        )
        self._pages.addWidget(self._alerts_page)
        self._settings_page = SettingsPage(
            current_interval_ms=self._monitoring_service.get_interval_ms(),
            current_baseline_multiplier=self._monitoring_service.get_baseline_multiplier(),
            rotation_enabled=self._rotation_enabled,
            profile_name=self._profile_name,
            parent=self._pages,
        )
        self._pages.addWidget(self._settings_page)

        content_layout.addWidget(self._pages)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content_shell, 1)

        self.setCentralWidget(root)

        self._nav_list.currentRowChanged.connect(self._on_navigation_changed)
        self._nav_list.setCurrentRow(0)
        self._devices_page.add_button.clicked.connect(self._add_device)
        self._devices_page.edit_button.clicked.connect(self._edit_selected_device)
        self._devices_page.delete_button.clicked.connect(self._delete_selected_device)
        self._settings_page.interval_left_button.clicked.connect(self._decrease_interval)
        self._settings_page.interval_right_button.clicked.connect(self._increase_interval)
        self._settings_page.baseline_left_button.clicked.connect(self._decrease_baseline)
        self._settings_page.baseline_right_button.clicked.connect(self._increase_baseline)
        self._settings_page.rotation_left_button.clicked.connect(self._decrease_rotation)
        self._settings_page.rotation_right_button.clicked.connect(self._increase_rotation)
        self._settings_page.profile_left_button.clicked.connect(self._decrease_profile)
        self._settings_page.profile_right_button.clicked.connect(self._increase_profile)
        self._status_value_label.clicked.connect(self._toggle_monitoring)
        for severity_button in self._alerts_page.severity_filter_buttons:
            severity_button.toggled.connect(
                lambda checked: self._refresh_alerts_page() if checked else None
            )
        self._alerts_page.unack_only_checkbox.stateChanged.connect(
            lambda _: self._refresh_alerts_page()
        )
        self._alerts_page.ack_button.clicked.connect(self._acknowledge_checked_alerts)

        self._overview_timer = QTimer(self)
        self._overview_timer.setInterval(self._monitoring_service.get_interval_ms())
        self._overview_timer.timeout.connect(self._refresh_overview_metrics)
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(1000)
        self._status_timer.timeout.connect(self._update_status_indicator)
        self._alerts_elapsed_timer = QTimer(self)
        self._alerts_elapsed_timer.setInterval(1000)
        self._alerts_elapsed_timer.timeout.connect(self._tick_alert_cards)

    def showEvent(self, event) -> None:  # noqa: N802
        """Запустить мониторинг при отображении окна."""
        super().showEvent(event)
        self._alerts_elapsed_timer.start()
        self._set_monitoring_enabled(self._monitoring_enabled, refresh_now=True)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Остановить мониторинг перед закрытием окна."""
        self._alerts_elapsed_timer.stop()
        self._status_timer.stop()
        self._overview_timer.stop()
        self._monitoring_service.stop()
        super().closeEvent(event)

    def _refresh_overview_metrics(self) -> None:
        """Обновить карточки обзора актуальными данными мониторинга."""
        metrics = self._monitoring_service.get_overview_metrics()
        has_samples = metrics.last_sample_at is not None
        self._overview_page.set_metric_value(
            "Текущая скорость",
            self._format_speed(metrics.total_speed_bps),
            "Суммарный входящий поток по всем устройствам."
            if has_samples
            else "Данные трафика еще не поступали. Для локальной проверки можно включить demo mode.",
        )
        self._overview_page.set_metric_value(
            "Активные устройства",
            str(metrics.active_devices),
            "Устройства, от которых получены данные за последнюю минуту."
            if has_samples
            else "После появления первых замеров здесь появится активность по устройствам.",
        )
        self._overview_page.set_metric_value(
            "Аномалии за сутки",
            str(metrics.alerts_last_24h),
            "События, превысившие baseline-порог в 2 раза."
            if metrics.alerts_last_24h > 0
            else "Новых аномалий пока нет. Это нормально для пустой или новой базы.",
        )
        self._overview_page.set_metric_value(
            "Последнее обновление",
            self._format_last_updated(metrics.last_sample_at),
            "Время завершения последнего цикла мониторинга."
            if has_samples
            else "Мониторинг запущен, но в базе еще нет замеров.",
        )
        if self._pages.currentIndex() == 1:
            self._refresh_devices_page()
        self._settings_page.set_current_interval_ms(self._monitoring_service.get_interval_ms())
        self._settings_page.set_current_baseline_multiplier(self._monitoring_service.get_baseline_multiplier())
        self._settings_page.set_current_rotation_enabled(self._rotation_enabled)
        self._settings_page.set_current_profile(self._profile_name)
        self._update_status_indicator()

    def _refresh_devices_page(self) -> None:
        """Обновить карточки и таблицу на странице устройств."""
        rows = self._monitoring_service.get_device_table_rows()
        self._devices_page.set_rows(rows)

        total_devices = len(rows)
        risk_devices = sum(1 for row in rows if row.risk_level == "Высокий")
        created_cutoff = datetime.now() - timedelta(days=7)
        new_devices = sum(1 for row in rows if row.created_at is not None and row.created_at >= created_cutoff)
        covered_devices = sum(
            1 for row in rows if row.ip_address.strip() and row.updated_at is not None
        )
        coverage = (covered_devices / total_devices * 100) if total_devices > 0 else 0.0

        self._devices_page.set_metric_value("Всего устройств", str(total_devices))
        self._devices_page.set_metric_value("В зоне риска", str(risk_devices))
        self._devices_page.set_metric_value("Новые за 7 дней", str(new_devices))
        self._devices_page.set_metric_value("Покрытие мониторинга", f"{coverage:.0f}%")
        if total_devices == 0:
            self._devices_page.set_metric_value(
                "Всего устройств",
                "0",
                "Список пуст. В обычном режиме устройства больше не создаются автоматически.",
            )
            self._devices_page.set_metric_value(
                "Покрытие мониторинга",
                "0%",
                "Покрытие появится после добавления устройств и получения первых замеров.",
            )

    def _add_device(self) -> None:
        """Открыть диалог добавления устройства."""
        dialog = DeviceDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            name, ip_value, mac_value = dialog.validated_values()
            self._monitoring_service.create_device(name, ip_value, mac_value)
        except ValueError as error:
            QMessageBox.warning(self, "Некорректные данные", str(error))
            return

        self._refresh_devices_page()
        self._refresh_overview_metrics()

    def _edit_selected_device(self) -> None:
        """Открыть диалог редактирования выбранного устройства."""
        device_id = self._devices_page.selected_device_id()
        if device_id is None:
            return

        device = next((item for item in self._monitoring_service.list_devices() if item.id == device_id), None)
        if device is None:
            QMessageBox.warning(self, "Устройство не найдено", "Не удалось загрузить выбранное устройство.")
            return

        dialog = DeviceDialog(device=device, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            name, ip_value, mac_value = dialog.validated_values()
            self._monitoring_service.update_device(device_id, name, ip_value, mac_value)
        except ValueError as error:
            QMessageBox.warning(self, "Некорректные данные", str(error))
            return

        self._refresh_devices_page()
        self._refresh_overview_metrics()

    def _delete_selected_device(self) -> None:
        """Удалить выбранное устройство после подтверждения."""
        device_id = self._devices_page.selected_device_id()
        if device_id is None:
            return

        device = next((item for item in self._monitoring_service.list_devices() if item.id == device_id), None)
        if device is None:
            QMessageBox.warning(self, "Устройство не найдено", "Не удалось загрузить выбранное устройство.")
            return

        result = QMessageBox.question(
            self,
            "Удалить устройство",
            f"Удалить устройство '{device.name}'?\nСвязанные замеры и оповещения тоже будут удалены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        self._monitoring_service.delete_device(device_id)
        self._refresh_devices_page()
        self._refresh_overview_metrics()

    def _on_navigation_changed(self, index: int) -> None:
        """Переключить страницу и точечно обновить данные активного раздела."""
        self._pages.setCurrentIndex(index)
        if index == 1:
            self._refresh_devices_page()
        elif index == 2:
            self._refresh_alerts_page()

    def _refresh_alerts_page(self) -> None:
        """Обновить карточки и таблицу на странице оповещений."""
        self._render_alert_cards()

        rows = self._monitoring_service.get_alert_table_rows(
            severity_filter=self._alerts_page.selected_severity_filter(),
            only_unacknowledged=self._alerts_page.only_unacknowledged(),
            limit=400,
        )
        if rows:
            self._alerts_page.set_empty_state_message("")
        else:
            self._alerts_page.set_empty_state_message(self._build_alerts_empty_state_message())
        self._alerts_page.set_rows(rows)

    def _tick_alert_cards(self) -> None:
        """Раз в секунду обновить подписи карточек на странице оповещений."""
        if self._pages.currentIndex() != 2:
            return
        self._render_alert_cards()

    def _render_alert_cards(self) -> None:
        """Обновить значения и подписи карточек раздела оповещений."""
        metrics = self._monitoring_service.get_alert_metrics()
        last_times = self._monitoring_service.get_alert_last_times()
        self._alerts_page.set_metric_value(
            "Критичные",
            str(metrics.high_count),
            self._alert_caption("Неподтвержденные события с высоким уровнем риска.", last_times.high_last_at),
        )
        self._alerts_page.set_metric_value(
            "Средние",
            str(metrics.medium_count),
            self._alert_caption(
                "Неподтвержденные отклонения, которые стоит перепроверить.",
                last_times.medium_last_at,
            ),
        )
        self._alerts_page.set_metric_value(
            "Низкие",
            str(metrics.low_count),
            self._alert_caption("Неподтвержденные информационные предупреждения.", last_times.low_last_at),
        )
        self._alerts_page.set_metric_value(
            "Подтверждено",
            str(metrics.acknowledged_count),
            self._alert_caption("Оповещения, по которым завершена проверка.", last_times.acknowledged_last_at),
        )

    def _build_alerts_empty_state_message(self) -> str:
        """Собрать сообщение пустого состояния для страницы оповещений."""
        severity_filter = self._alerts_page.selected_severity_filter()
        only_unack = self._alerts_page.only_unacknowledged()

        if severity_filter is None and not only_unack:
            return (
                "Оповещений пока нет.\n"
                "Это нормально для новой базы без demo-данных или без реальных событий мониторинга."
            )
        if severity_filter is None and only_unack:
            return (
                "Неподтвержденных оповещений сейчас нет.\n"
                "Попробуйте снять фильтр или дождитесь новых событий."
            )

        severity_text = {
            "high": "критичного",
            "medium": "среднего",
            "low": "низкого",
        }.get(severity_filter, "выбранного")

        if only_unack:
            return (
                f"Неподтвержденных оповещений {severity_text} уровня сейчас нет.\n"
                "Попробуйте изменить фильтр или дождитесь новых событий."
            )
        return (
            f"Оповещений {severity_text} уровня пока нет.\n"
            "Попробуйте изменить фильтр или включить demo mode для проверки UI."
        )

    def _acknowledge_checked_alerts(self) -> None:
        """Подтвердить выбранные оповещения из таблицы."""
        checked = self._alerts_page.checked_alerts()
        if not checked:
            return
        for alert_id, acknowledged in checked:
            if acknowledged:
                continue
            self._monitoring_service.set_alert_acknowledged(alert_id, True)
        self._refresh_alerts_page()

    def _decrease_interval(self) -> None:
        """Уменьшить интервал мониторинга на один шаг."""
        interval_ms = self._settings_page.step_interval(-1)
        self._apply_interval_setting(interval_ms)

    def _increase_interval(self) -> None:
        """Увеличить интервал мониторинга на один шаг."""
        interval_ms = self._settings_page.step_interval(1)
        self._apply_interval_setting(interval_ms)

    def _apply_interval_setting(self, interval_ms: int) -> None:
        """Применить значение интервала мониторинга."""
        self._monitoring_service.set_interval_ms(interval_ms)
        self._settings.setValue("monitoring_interval_ms", interval_ms)
        self._overview_timer.setInterval(interval_ms)
        if self._monitoring_enabled and self._overview_timer.isActive():
            self._overview_timer.start(interval_ms)
        self._settings_page.set_current_interval_ms(interval_ms)
        self._update_status_indicator()
        self._refresh_overview_metrics()

    def _decrease_baseline(self) -> None:
        """Уменьшить множитель baseline на один шаг."""
        multiplier = self._settings_page.step_baseline(-1)
        self._apply_baseline_setting(multiplier)

    def _increase_baseline(self) -> None:
        """Увеличить множитель baseline на один шаг."""
        multiplier = self._settings_page.step_baseline(1)
        self._apply_baseline_setting(multiplier)

    def _apply_baseline_setting(self, multiplier: float) -> None:
        """Применить множитель baseline."""
        self._monitoring_service.set_baseline_multiplier(multiplier)
        self._settings.setValue("baseline_multiplier", multiplier)
        self._settings_page.set_current_baseline_multiplier(multiplier)
        self._refresh_overview_metrics()

    def _decrease_rotation(self) -> None:
        """Сместить состояние ротации логов влево."""
        enabled = self._settings_page.step_rotation(-1)
        self._apply_rotation_setting(enabled)

    def _increase_rotation(self) -> None:
        """Сместить состояние ротации логов вправо."""
        enabled = self._settings_page.step_rotation(1)
        self._apply_rotation_setting(enabled)

    def _apply_rotation_setting(self, enabled: bool) -> None:
        """Применить состояние ротации логов."""
        self._rotation_enabled = enabled
        self._settings.setValue("log_rotation_enabled", enabled)
        self._set_file_rotation_enabled(enabled)
        self._settings_page.set_current_rotation_enabled(enabled)
        self._refresh_overview_metrics()

    def _decrease_profile(self) -> None:
        """Переключить профиль влево."""
        profile_name = self._settings_page.step_profile(-1)
        self._apply_profile_setting(profile_name)

    def _increase_profile(self) -> None:
        """Переключить профиль вправо."""
        profile_name = self._settings_page.step_profile(1)
        self._apply_profile_setting(profile_name)

    def _apply_profile_setting(self, profile_name: str) -> None:
        """Применить профиль мониторинга."""
        self._profile_name = profile_name
        self._settings.setValue("monitoring_profile", profile_name)
        logging.getLogger(self.__class__.__name__).info("Monitoring profile switched to %s", profile_name)
        self._settings_page.set_current_profile(profile_name)
        self._refresh_overview_metrics()

    def _toggle_monitoring(self) -> None:
        """Переключить состояние мониторинга по нажатию на статус."""
        self._set_monitoring_enabled(not self._monitoring_enabled, refresh_now=True)

    def _set_monitoring_enabled(self, enabled: bool, refresh_now: bool) -> None:
        """Включить или выключить мониторинг и синхронизировать таймеры."""
        self._monitoring_enabled = enabled
        if enabled:
            self._monitoring_service.start()
            if refresh_now:
                self._refresh_overview_metrics()
            self._overview_timer.start()
            self._status_timer.start()
        else:
            self._status_timer.stop()
            self._overview_timer.stop()
            self._monitoring_service.stop()
            if refresh_now:
                self._refresh_overview_metrics()
        self._update_status_indicator()

    def _update_status_indicator(self) -> None:
        """Обновить текст состояния мониторинга."""
        if self._monitoring_enabled:
            self._status_value_label.setProperty("active", True)
            remaining_ms = self._overview_timer.remainingTime()
            if remaining_ms < 0:
                remaining_ms = self._monitoring_service.get_interval_ms()
            self._status_value_label.setText(f"Активен • {self._format_remaining_time(remaining_ms)}")
            self._status_value_label.setToolTip("Таймер до следующего обновления мониторинга.")
        else:
            self._status_value_label.setProperty("active", False)
            self._status_value_label.setText("Неактивен")
            self._status_value_label.setToolTip("Мониторинг остановлен. Нажмите, чтобы запустить.")
        self._status_value_label.style().unpolish(self._status_value_label)
        self._status_value_label.style().polish(self._status_value_label)
        self._status_value_label.update()

    def _alert_caption(self, base_text: str, last_at: datetime | None) -> str:
        """Сформировать подпись карточки с собственным временем последнего события."""
        if last_at is None:
            return f"{base_text}\nПоследнее срабатывание: нет данных."
        elapsed = datetime.now() - last_at
        return f"{base_text}\nПоследнее срабатывание: {self._format_elapsed_delta(elapsed)} назад."

    def _apply_saved_interval(self) -> None:
        """Загрузить сохраненный интервал и применить его к мониторингу."""
        allowed_intervals = {value for _, value in INTERVAL_OPTIONS}
        stored_value = self._settings.value(
            "monitoring_interval_ms",
            self._monitoring_service.get_interval_ms(),
            type=int,
        )
        if stored_value in allowed_intervals:
            self._monitoring_service.set_interval_ms(stored_value)

    def _apply_saved_baseline(self) -> None:
        """Загрузить сохраненный baseline и применить его к мониторингу."""
        stored_value = self._settings.value(
            "baseline_multiplier",
            self._monitoring_service.get_baseline_multiplier(),
            type=float,
        )
        if any(abs(stored_value - option) < 1e-9 for option in BASELINE_OPTIONS):
            self._monitoring_service.set_baseline_multiplier(stored_value)

    def _load_saved_rotation(self) -> None:
        """Загрузить сохраненное состояние ротации логов."""
        stored_value = self._settings.value("log_rotation_enabled", True, type=bool)
        self._rotation_enabled = bool(stored_value)
        self._set_file_rotation_enabled(self._rotation_enabled)

    def _load_saved_profile(self) -> None:
        """Загрузить сохраненный профиль."""
        stored_value = self._settings.value("monitoring_profile", PROFILE_OPTIONS[0], type=str)
        if stored_value in PROFILE_OPTIONS:
            self._profile_name = stored_value
        else:
            self._profile_name = PROFILE_OPTIONS[0]

    @staticmethod
    def _set_file_rotation_enabled(enabled: bool) -> None:
        """Включить или выключить ротацию для файловых лог-хендлеров."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, RotatingFileHandler):
                handler.maxBytes = DEFAULT_ROTATING_LOG_MAX_BYTES if enabled else 0

    @staticmethod
    def _format_speed(bytes_per_second: float) -> str:
        """Форматировать скорость в читабельный вид (Б/с, КБ/с, МБ/с)."""
        if bytes_per_second < 1024:
            return f"{bytes_per_second:.0f} Б/с"
        if bytes_per_second < 1024 * 1024:
            return f"{bytes_per_second / 1024:.1f} КБ/с"
        return f"{bytes_per_second / (1024 * 1024):.2f} МБ/с"

    @staticmethod
    def _format_last_updated(last_sample_at: datetime | None) -> str:
        """Форматировать время последнего обновления для UI."""
        if last_sample_at is None:
            return "нет данных"
        return last_sample_at.strftime("%H:%M:%S")

    @staticmethod
    def _format_remaining_time(remaining_ms: int) -> str:
        """Форматировать оставшееся время до следующего обновления."""
        total_seconds = max(1, int((max(0, remaining_ms) + 999) // 1000))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours} ч {minutes:02d} мин"
        if minutes > 0:
            return f"{minutes} мин {seconds:02d} сек"
        return f"{seconds} сек"

    @staticmethod
    def _format_elapsed_delta(delta: timedelta) -> str:
        """Форматировать прошедшее время для страницы оповещений."""
        total_seconds = max(0, int(delta.total_seconds()))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours} ч {minutes:02d} мин"
        if minutes > 0:
            return f"{minutes} мин {seconds:02d} сек"
        return f"{seconds} сек"


class DeviceDialog(QDialog):
    """Диалог создания или редактирования устройства."""

    def __init__(self, device: Device | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить устройство" if device is None else "Изменить устройство")
        self.setModal(True)
        self.resize(420, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self._name_input = QLineEdit(self)
        self._ip_input = QLineEdit(self)
        self._mac_input = QLineEdit(self)
        self._name_input.setPlaceholderText("Например, WiFi Camera")
        self._ip_input.setPlaceholderText("192.168.1.20")
        self._mac_input.setPlaceholderText("AA:BB:CC:DD:EE:FF")

        if device is not None:
            self._name_input.setText(device.name)
            self._ip_input.setText(device.ip_address)
            self._mac_input.setText(device.mac_address or "")

        form.addRow("Название", self._name_input)
        form.addRow("IP-адрес", self._ip_input)
        form.addRow("MAC-адрес", self._mac_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)

    def validated_values(self) -> tuple[str, str, str | None]:
        """Вернуть провалидированные значения формы."""
        name = self._name_input.text().strip()
        ip_value = self._ip_input.text().strip()
        mac_value = self._mac_input.text().strip() or None

        if not name:
            raise ValueError("Укажите название устройства.")
        if not ip_value:
            raise ValueError("Укажите IP-адрес устройства.")

        try:
            ip_address(ip_value)
        except ValueError as error:
            raise ValueError("IP-адрес указан в неверном формате.") from error

        if mac_value is not None and not MAC_ADDRESS_RE.fullmatch(mac_value):
            raise ValueError("MAC-адрес должен быть в формате AA:BB:CC:DD:EE:FF.")

        return name, ip_value, mac_value.upper() if mac_value is not None else None
