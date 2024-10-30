import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QKeyEvent
import speech_recognition as sr
import pyttsx3
import json
import os
import logging
from datetime import datetime
import pyautogui
import webbrowser
import sys
import winreg as reg
import sounddevice as sd


class ThemeManager:
    def __init__(self):
        self.light_theme = """
            QMainWindow, QDialog {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background: #f5f5f5;
            }
            QTabBar::tab {
                background: #e0e0e0;
                padding: 8px 16px;
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #2196F3;
                color: white;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QTableWidget {
                background: white;
                border: 1px solid #ddd;
            }
            QTextEdit {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QComboBox {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QSpinBox {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QCheckBox {
                color: #333;
            }
        """

        self.dark_theme = """
            QMainWindow, QDialog {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #333;
                background: #1e1e1e;
            }
            QTabBar::tab {
                background: #2d2d2d;
                color: #ddd;
                padding: 8px 16px;
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #0d47a1;
                color: white;
            }
            QLabel {
                color: #ddd;
            }
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QTableWidget {
                background: #2d2d2d;
                color: #ddd;
                border: 1px solid #333;
            }
            QTextEdit {
                background: #2d2d2d;
                color: #ddd;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QComboBox {
                background: #2d2d2d;
                color: #ddd;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 5px;
            }
            QSpinBox {
                background: #2d2d2d;
                color: #ddd;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 5px;
            }
            QCheckBox {
                color: #ddd;
            }
        """


class VoiceThread(QThread):
    textDetected = pyqtSignal(str)
    statusUpdate = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.recognition_language = 'ru-RU'
        self.microphone = None

    def run(self):
        self.is_listening = True
        while self.is_listening:
            try:
                if self.microphone is None:
                    self.microphone = sr.Microphone()

                with self.microphone as source:
                    self.statusUpdate.emit("Слушаю...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self.recognizer.listen(source, timeout=5)
                    self.statusUpdate.emit("Обработка речи...")
                    text = self.recognizer.recognize_google(audio, language=self.recognition_language)
                    self.textDetected.emit(text.lower())
            except sr.UnknownValueError:
                self.statusUpdate.emit("Речь не распознана")
            except sr.RequestError:
                self.statusUpdate.emit("Ошибка сервиса распознавания")
            except Exception as e:
                self.statusUpdate.emit(f"Ошибка: {str(e)}")

    def stop(self):
        self.is_listening = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()
        self.current_theme = "light"
        self.initUI()
        self.loadCommands()
        self.initVoiceAssistant()
        self.initTrayIcon()
        self.setupLogging()
        self.loadSettings()
        self.populateAudioDevices()

    def sendTextCommand(self):
        text = self.command_input.toPlainText().strip()
        if text:
            self.logMessage(f"Введена команда: {text}")
            self.executeCommand(text)
            self.command_input.clear()

    def populateAudioDevices(self):
        try:
            # Получение списка аудио устройств
            devices = sd.query_devices()

            # Очистка комбобоксов
            self.output_devices.clear()
            self.input_devices.clear()

            # Заполнение устройств вывода
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    self.output_devices.addItem(device['name'], i)

            # Заполнение устройств ввода
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    self.input_devices.addItem(device['name'], i)

            # Установка текущих устройств
            default_output = sd.default.device[1]
            default_input = sd.default.device[0]

            if default_output is not None:
                index = self.output_devices.findData(default_output)
                if index >= 0:
                    self.output_devices.setCurrentIndex(index)

            if default_input is not None:
                index = self.input_devices.findData(default_input)
                if index >= 0:
                    self.input_devices.setCurrentIndex(index)

        except Exception as e:
            self.logMessage(f"Ошибка при получении списка аудио устройств: {str(e)}")

    def initUI(self):
        self.setWindowTitle('Голосовой ассистент')
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Верхняя панель
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)

        self.theme_button = QPushButton()
        self.theme_button.setIcon(QIcon('light.png'))
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setFixedSize(40, 40)

        self.status_label = QLabel("Статус: Готов к работе")
        self.status_label.setStyleSheet("padding: 5px; border-radius: 4px;")

        self.start_button = QPushButton('Начать прослушивание')
        self.start_button.clicked.connect(self.startListening)

        self.stop_button = QPushButton('Остановить')
        self.stop_button.clicked.connect(self.stopListening)
        self.stop_button.setEnabled(False)

        top_layout.addWidget(self.theme_button)
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        top_layout.addWidget(self.start_button)
        top_layout.addWidget(self.stop_button)

        main_layout.addWidget(top_panel)

        # Вкладки
        self.tab_widget = QTabWidget()

        # Вкладка команд
        self.commands_tab = QWidget()
        self.setup_commands_tab()
        self.tab_widget.addTab(self.commands_tab, "Редактор команд")

        # Вкладка настроек
        self.settings_tab = QWidget()
        self.setup_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Настройки")

        # Вкладка журнала
        self.log_tab = QWidget()
        self.setup_log_tab()
        self.tab_widget.addTab(self.log_tab, "Журнал")

        main_layout.addWidget(self.tab_widget)

        self.apply_theme(self.current_theme)

    def setup_commands_tab(self):
        layout = QVBoxLayout(self.commands_tab)

        # Панель инструментов для команд
        tools_layout = QHBoxLayout()

        add_btn = QPushButton('Добавить команду')
        add_btn.setIcon(QIcon('add.png'))  # Добавьте соответствующую иконку
        add_btn.setIconSize(QSize(20, 20))
        add_btn.setMinimumWidth(150)
        add_btn.clicked.connect(self.addCommand)

        remove_btn = QPushButton('Удалить команду')
        remove_btn.setIcon(QIcon('remove.png'))  # Добавьте соответствующую иконку
        remove_btn.setIconSize(QSize(20, 20))
        remove_btn.setMinimumWidth(150)
        remove_btn.clicked.connect(self.removeCommand)

        tools_layout.addWidget(add_btn)
        tools_layout.addWidget(remove_btn)
        tools_layout.addStretch()

        layout.addLayout(tools_layout)

        # Таблица команд
        self.command_table = QTableWidget()
        self.command_table.setColumnCount(3)
        self.command_table.setHorizontalHeaderLabels(['Категория', 'Команда', 'Действие'])

        # Настройка внешнего вида таблицы
        self.command_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: transparent;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #ddd;
                font-weight: bold;
            }
            QTableWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)

        # Настройка заголовков таблицы
        header = self.command_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        # Дополнительные настройки таблицы
        self.command_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.command_table.setSelectionMode(QTableWidget.SingleSelection)
        self.command_table.setShowGrid(False)
        self.command_table.verticalHeader().setVisible(False)
        self.command_table.setFocusPolicy(Qt.StrongFocus)

        # Добавляем поиск
        search_layout = QHBoxLayout()
        search_label = QLabel("Поиск:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите текст для поиска...")
        self.search_input.textChanged.connect(self.filterCommands)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)
        layout.addWidget(self.command_table)

    def filterCommands(self, text):
        """Фильтрация команд в таблице"""
        for row in range(self.command_table.rowCount()):
            match = False
            for column in range(self.command_table.columnCount()):
                item = self.command_table.item(row, column)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.command_table.setRowHidden(row, not match)

    def updateCommandTable(self):
        """Обновленный метод заполнения таблицы"""
        self.command_table.setRowCount(0)
        row = 0
        for category, commands in self.commands.items():
            for command, action in commands.items():
                self.command_table.insertRow(row)

                # Создаем и настраиваем элементы таблицы
                category_item = QTableWidgetItem(category)
                command_item = QTableWidgetItem(command)
                action_item = QTableWidgetItem(action)

                # Устанавливаем выравнивание и стили
                category_item.setTextAlignment(Qt.AlignCenter)
                command_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                action_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

                # Добавляем элементы в таблицу
                self.command_table.setItem(row, 0, category_item)
                self.command_table.setItem(row, 1, command_item)
                self.command_table.setItem(row, 2, action_item)

                row += 1

        # Подгоняем размеры столбцов
        self.command_table.resizeColumnsToContents()

    def setupContextMenu(self):
        self.command_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.command_table.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, position):
        menu = QMenu()
        edit_action = menu.addAction("Редактировать")
        delete_action = menu.addAction("Удалить")
        copy_action = menu.addAction("Копировать")

        action = menu.exec_(self.command_table.mapToGlobal(position))

        if action == edit_action:
            self.editCurrentCommand()
        elif action == delete_action:
            self.removeCommand()
        elif action == copy_action:
            self.copyCommand()

    def setup_settings_tab(self):
        layout = QVBoxLayout(self.settings_tab)

        form_layout = QFormLayout()

        # Настройки голоса
        self.voice_speed = QSpinBox()
        self.voice_speed.setRange(50, 300)
        form_layout.addRow('Скорость речи:', self.voice_speed)

        self.voice_volume = QSpinBox()
        self.voice_volume.setRange(0, 100)
        form_layout.addRow('Громкость речи (%):', self.voice_volume)

        # Настройки системы
        self.autostart = QCheckBox('Запускать при старте Windows')
        form_layout.addRow(self.autostart)

        self.minimize_to_tray = QCheckBox('Сворачивать в трей')
        form_layout.addRow(self.minimize_to_tray)

        # Настройки языка
        self.language = QComboBox()
        self.language.addItems(['Русский', 'English'])
        form_layout.addRow('Язык распознавания:', self.language)

        # Аудио устройства
        self.output_devices = QComboBox()
        self.input_devices = QComboBox()
        form_layout.addRow('Устройство вывода:', self.output_devices)
        form_layout.addRow('Устройство ввода:', self.input_devices)

        layout.addLayout(form_layout)

        # Кнопка применения настроек
        apply_btn = QPushButton('Применить настройки')
        apply_btn.clicked.connect(self.applySettings)
        layout.addWidget(apply_btn)
        layout.addStretch()

    def setup_log_tab(self):
        layout = QVBoxLayout(self.log_tab)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Панель ввода команд
        input_panel = QWidget()
        input_layout = QHBoxLayout(input_panel)

        self.command_input = CommandTextEdit(self)
        self.command_input.setMaximumHeight(50)
        self.command_input.setPlaceholderText("Введите команду здесь...")

        send_btn = QPushButton('Отправить')
        send_btn.clicked.connect(self.sendTextCommand)

        input_layout.addWidget(self.command_input)
        input_layout.addWidget(send_btn)

        layout.addWidget(input_panel)

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(self.current_theme)
        self.saveSettings()

    def apply_theme(self, theme):
        if theme == "light":
            self.setStyleSheet(self.theme_manager.light_theme)
            self.theme_button.setIcon(QIcon('dark.png'))
        else:
            self.setStyleSheet(self.theme_manager.dark_theme)
            self.theme_button.setIcon(QIcon('light.png'))

    def applySettings(self):
        try:
            # Применяем настройки голосового движка
            self.engine.setProperty('rate', self.voice_speed.value())
            self.engine.setProperty('volume', self.voice_volume.value() / 100)

            # Установка языка распознавания
            if self.language.currentText() == 'Русский':
                self.voice_thread.recognition_language = 'ru-RU'
            else:
                self.voice_thread.recognition_language = 'en-US'

            # Настройка автозапуска
            key = reg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

            try:
                registry_key = reg.OpenKey(key, key_path, 0, reg.KEY_ALL_ACCESS)
                if self.autostart.isChecked():
                    reg.SetValueEx(registry_key, "VoiceAssistant", 0, reg.REG_SZ, sys.argv[0])
                else:
                    try:
                        reg.DeleteValue(registry_key, "VoiceAssistant")
                    except WindowsError:
                        pass
                reg.CloseKey(registry_key)
            except WindowsError:
                self.logMessage("Не удалось настроить автозапуск")

            # Сохранение настроек в файл
            self.saveSettings()

            # Обновление устройств ввода-вывода
            if hasattr(self, 'output_devices') and hasattr(self, 'input_devices'):
                output_device_index = self.output_devices.currentData()
                input_device_index = self.input_devices.currentData()

                if output_device_index is not None:
                    sd.default.device[1] = output_device_index
                if input_device_index is not None:
                    sd.default.device[0] = input_device_index
                    self.voice_thread.microphone = None  # Сброс микрофона для переинициализации

            QMessageBox.information(self, "Успех", "Настройки успешно применены")
            self.logMessage("Настройки применены")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось применить настройки: {str(e)}")
            self.logMessage(f"Ошибка при применении настроек: {str(e)}")

    def initVoiceAssistant(self):
        self.voice_thread = VoiceThread()
        self.voice_thread.textDetected.connect(self.onTextDetected)
        self.voice_thread.statusUpdate.connect(self.updateStatus)
        self.engine = pyttsx3.init()

    def initTrayIcon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        tray_menu = QMenu()
        show_action = tray_menu.addAction("Показать")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Выход")
        quit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def setupLogging(self):
        logging.basicConfig(
            filename=f'voice_assistant_{datetime.now().strftime("%Y%m%d")}.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def loadSettings(self):
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.current_theme = settings.get('theme', 'light')
                self.voice_speed.setValue(settings.get('voice_speed', 180))
                self.voice_volume.setValue(settings.get('voice_volume', 100))
                self.autostart.setChecked(settings.get('autostart', False))
                self.minimize_to_tray.setChecked(settings.get('minimize_to_tray', True))
                self.language.setCurrentText(settings.get('language', 'Русский'))

                self.apply_theme(self.current_theme)
        except FileNotFoundError:
            self.setDefaultSettings()

    def saveSettings(self):
        settings = {
            'theme': self.current_theme,
            'voice_speed': self.voice_speed.value(),
            'voice_volume': self.voice_volume.value(),
            'autostart': self.autostart.isChecked(),
            'minimize_to_tray': self.minimize_to_tray.isChecked(),
            'language': self.language.currentText(),
            'output_device': {
                'name': self.output_devices.currentText(),
                'index': self.output_devices.currentData()
            },
            'input_device': {
                'name': self.input_devices.currentText(),
                'index': self.input_devices.currentData()
            }
        }

        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    def setDefaultSettings(self):
        self.current_theme = "light"
        self.voice_speed.setValue(180)
        self.voice_volume.setValue(100)
        self.autostart.setChecked(False)
        self.minimize_to_tray.setChecked(True)
        self.language.setCurrentText('Русский')
        self.apply_theme(self.current_theme)

    def startListening(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.voice_thread.start()
        self.updateStatus("Прослушивание активно")

    def stopListening(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.voice_thread.stop()
        self.updateStatus("Прослушивание остановлено")

    def updateStatus(self, status):
        self.status_label.setText(f"Статус: {status}")
        self.logMessage(status)

    def logMessage(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        logging.info(message)

    def onTextDetected(self, text):
        self.logMessage(f"Распознано: {text}")
        self.executeCommand(text)

    def loadCommands(self):
        try:
            with open('commands.json', 'r', encoding='utf-8') as file:
                self.commands = json.load(file)
            self.updateCommandTable()
        except FileNotFoundError:
            self.commands = {
                "системные": {
                    "выключить компьютер": "shutdown",
                    "перезагрузить": "restart"
                },
                "приложения": {
                    "открыть браузер": "browser",
                    "открыть блокнот": "notepad"
                }
            }
            self.saveCommands()

    def updateCommandTable(self):
        self.command_table.setRowCount(0)
        row = 0
        for category, commands in self.commands.items():
            for command, action in commands.items():
                self.command_table.insertRow(row)
                self.command_table.setItem(row, 0, QTableWidgetItem(category))
                self.command_table.setItem(row, 1, QTableWidgetItem(command))
                self.command_table.setItem(row, 2, QTableWidgetItem(action))
                row += 1

    def saveCommands(self):
        with open('commands.json', 'w', encoding='utf-8') as file:
            json.dump(self.commands, file, ensure_ascii=False, indent=4)

    def addCommand(self):
        dialog = CommandConstructorDialog(self)
        dialog.exec_()

    def removeCommand(self):
        current_row = self.command_table.currentRow()
        if current_row >= 0:
            category = self.command_table.item(current_row, 0).text()
            command = self.command_table.item(current_row, 1).text()

            reply = QMessageBox.question(
                self, 'Подтверждение',
                f'Вы уверены, что хотите удалить команду "{command}"?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)

            if reply == QMessageBox.Yes:
                del self.commands[category][command]
                self.saveCommands()
                self.updateCommandTable()
                self.logMessage(f"Удалена команда: {command}")

    def executeCommand(self, text):
        for category, commands in self.commands.items():
            if text in commands:
                action = commands[text]
                self.logMessage(f"Выполняется команда: {action}")

                try:
                    if action.startswith("system:"):
                        command = action.replace("system:", "", 1)
                        os.system(command)
                        self.speak("Выполняю системную команду")

                    elif action.startswith("app:"):
                        path = action.replace("app:", "", 1)
                        os.startfile(path)
                        self.speak("Запускаю приложение")

                    elif action.startswith("url:"):
                        url = action.replace("url:", "", 1)
                        webbrowser.open(url)
                        self.speak("Открываю веб-страницу")

                    elif action.startswith("script:"):
                        script = action.replace("script:", "", 1)
                        exec(script)
                        self.speak("Выполняю скрипт")

                    else:
                        # Поддержка старых команд
                        if action == "shutdown":
                            os.system("shutdown /s /t 60")
                            self.speak("Компьютер будет выключен через минуту")
                        elif action == "restart":
                            os.system("shutdown /r /t 60")
                            self.speak("Компьютер будет перезагружен через минуту")
                        elif action == "browser":
                            webbrowser.open('http://google.com')
                            self.speak("Открываю браузер")
                        elif action == "notepad":
                            os.system("notepad")
                            self.speak("Открываю блокнот")

                except Exception as e:
                    self.logMessage(f"Ошибка при выполнении команды: {str(e)}")
                    self.speak("Произошла ошибка при выполнении команды")
                break

    def speak(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            self.logMessage(f"Ассистент: {text}")
        except Exception as e:
            self.logMessage(f"Ошибка воспроизведения речи: {str(e)}")

    def closeEvent(self, event):
        if hasattr(self, 'minimize_to_tray') and self.minimize_to_tray and not self.isHidden():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Голосовой ассистент",
                "Приложение свернуто в трей",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            if self.voice_thread.is_listening:
                self.voice_thread.stop()
            event.accept()

class CommandTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            self.parent.sendTextCommand()
        else:
            super().keyPressEvent(event)

class CommandConstructorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Конструктор команд')
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)

        # Выбор категории
        category_layout = QHBoxLayout()
        category_label = QLabel('Категория:')
        self.category_combo = QComboBox()
        self.category_combo.addItems(['системные', 'приложения'])
        self.category_combo.setEditable(True)
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)

        # Ввод команды
        command_layout = QHBoxLayout()
        command_label = QLabel('Команда:')
        self.command_input = QTextEdit()
        self.command_input.setMaximumHeight(50)
        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input)
        layout.addLayout(command_layout)

        # Выбор типа действия
        action_type_layout = QHBoxLayout()
        action_type_label = QLabel('Тип действия:')
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(
            ['Системная команда', 'Открытие приложения', 'Открытие URL', 'Пользовательский скрипт'])
        self.action_type_combo.currentIndexChanged.connect(self.onActionTypeChanged)
        action_type_layout.addWidget(action_type_label)
        action_type_layout.addWidget(self.action_type_combo)
        layout.addLayout(action_type_layout)

        # Стек виджетов для разных типов действий
        self.action_stack = QStackedWidget()

        # Системная команда
        system_widget = QWidget()
        system_layout = QVBoxLayout(system_widget)
        self.system_command_input = QTextEdit()
        system_layout.addWidget(QLabel('Введите системную команду:'))
        system_layout.addWidget(self.system_command_input)

        # Открытие приложения
        app_widget = QWidget()
        app_layout = QVBoxLayout(app_widget)
        self.app_path_input = QTextEdit()
        browse_btn = QPushButton('Обзор...')
        browse_btn.clicked.connect(self.browseApplication)
        app_layout.addWidget(QLabel('Путь к приложению:'))
        app_layout.addWidget(self.app_path_input)
        app_layout.addWidget(browse_btn)

        # URL
        url_widget = QWidget()
        url_layout = QVBoxLayout(url_widget)
        self.url_input = QTextEdit()
        url_layout.addWidget(QLabel('Введите URL:'))
        url_layout.addWidget(self.url_input)

        # Пользовательский скрипт
        script_widget = QWidget()
        script_layout = QVBoxLayout(script_widget)
        self.script_input = QTextEdit()
        script_layout.addWidget(QLabel('Введите Python-скрипт:'))
        script_layout.addWidget(self.script_input)

        self.action_stack.addWidget(system_widget)
        self.action_stack.addWidget(app_widget)
        self.action_stack.addWidget(url_widget)
        self.action_stack.addWidget(script_widget)

        layout.addWidget(self.action_stack)

        # Кнопки
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(self.saveCommand)
        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

    def onActionTypeChanged(self, index):
        self.action_stack.setCurrentIndex(index)

    def browseApplication(self):
        file_name, _ = QFileDialog.getOpenFileName(self, 'Выберите приложение', '',
                                                    'Executable files (*.exe);;All files (*.*)')
        if file_name:
            self.app_path_input.setText(file_name)

    def saveCommand(self):
        category = self.category_combo.currentText()
        command = self.command_input.toPlainText().strip()

        if not category or not command:
            QMessageBox.warning(self, 'Ошибка', 'Заполните все поля')
            return

        action_type = self.action_type_combo.currentIndex()
        action = ""

        if action_type == 0:  # Системная команда
            action = f"system:{self.system_command_input.toPlainText()}"
        elif action_type == 1:  # Приложение
            action = f"app:{self.app_path_input.toPlainText()}"
        elif action_type == 2:  # URL
            action = f"url:{self.url_input.toPlainText()}"
        elif action_type == 3:  # Скрипт
            action = f"script:{self.script_input.toPlainText()}"

        if not action:
            QMessageBox.warning(self, 'Ошибка', 'Заполните действие')
            return

        if category not in self.parent.commands:
            self.parent.commands[category] = {}

        self.parent.commands[category][command] = action
        self.parent.saveCommands()
        self.parent.updateCommandTable()
        self.parent.logMessage(f"Добавлена новая команда: {command}")

        self.accept()

def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()