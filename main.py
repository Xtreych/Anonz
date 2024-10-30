import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QTextEdit,
                             QTableWidget, QTableWidgetItem, QComboBox,
                             QMessageBox, QInputDialog, QSystemTrayIcon, QMenu,
                             QStyle, QDialog, QTabWidget, QSpinBox, QCheckBox,
                             QFormLayout, QColorDialog, QFontDialog, QStackedWidget, QFileDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
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


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.initUI()
        self.loadSettings()

    def initUI(self):
        self.setWindowTitle('Настройки')
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Создаем вкладки
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Вкладка общих настроек
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)

        self.voice_speed = QSpinBox()
        self.voice_speed.setRange(50, 300)
        general_layout.addRow('Скорость речи:', self.voice_speed)

        self.voice_volume = QSpinBox()
        self.voice_volume.setRange(0, 100)
        general_layout.addRow('Громкость речи (%):', self.voice_volume)

        self.autostart = QCheckBox('Запускать при старте Windows')
        general_layout.addRow(self.autostart)

        self.minimize_to_tray = QCheckBox('Сворачивать в трей')
        general_layout.addRow(self.minimize_to_tray)

        tabs.addTab(general_tab, "Общие")

        # Вкладка аудио настроек
        audio_tab = QWidget()
        audio_layout = QFormLayout(audio_tab)

        self.output_devices = QComboBox()
        self.loadOutputDevices()
        audio_layout.addRow('Устройство вывода звука:', self.output_devices)

        self.input_devices = QComboBox()
        self.loadInputDevices()
        audio_layout.addRow('Устройство ввода звука (микрофон):', self.input_devices)

        refresh_btn = QPushButton('Обновить список устройств')
        refresh_btn.clicked.connect(self.refreshDevices)
        audio_layout.addRow(refresh_btn)

        tabs.addTab(audio_tab, "Аудио")

        # Вкладка настроек распознавания
        recognition_tab = QWidget()
        recognition_layout = QFormLayout(recognition_tab)

        self.language = QComboBox()
        self.language.addItems(['Русский', 'English'])
        recognition_layout.addRow('Язык распознавания:', self.language)

        self.continuous_recognition = QCheckBox('Непрерывное распознавание')
        recognition_layout.addRow(self.continuous_recognition)

        self.noise_reduction = QCheckBox('Шумоподавление')
        recognition_layout.addRow(self.noise_reduction)

        tabs.addTab(recognition_tab, "Распознавание")

        # Вкладка настроек интерфейса
        interface_tab = QWidget()
        interface_layout = QFormLayout(interface_tab)

        self.choose_color_btn = QPushButton('Выбрать цвет интерфейса')
        self.choose_color_btn.clicked.connect(self.chooseColor)
        interface_layout.addRow(self.choose_color_btn)

        self.choose_font_btn = QPushButton('Выбрать шрифт')
        self.choose_font_btn.clicked.connect(self.chooseFont)
        interface_layout.addRow(self.choose_font_btn)

        tabs.addTab(interface_tab, "Интерфейс")

        # Кнопки
        buttons_layout = QHBoxLayout()

        apply_btn = QPushButton('Применить')
        apply_btn.clicked.connect(self.applySettings)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(apply_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def loadOutputDevices(self):
        self.output_devices.clear()
        try:
            devices = sd.query_devices()
            for device in devices:
                if device['max_output_channels'] > 0:
                    self.output_devices.addItem(device['name'], device['index'])

            default_device = sd.query_devices(kind='output')
            default_index = self.output_devices.findText(default_device['name'])
            if default_index >= 0:
                self.output_devices.setCurrentIndex(default_index)

        except Exception as e:
            self.output_devices.addItem("Ошибка загрузки устройств")
            logging.error(f"Ошибка при загрузке устройств вывода: {str(e)}")

    def loadInputDevices(self):
        self.input_devices.clear()
        try:
            devices = sd.query_devices()
            for device in devices:
                if device['max_input_channels'] > 0:
                    self.input_devices.addItem(device['name'], device['index'])

            default_device = sd.query_devices(kind='input')
            default_index = self.input_devices.findText(default_device['name'])
            if default_index >= 0:
                self.input_devices.setCurrentIndex(default_index)

        except Exception as e:
            self.input_devices.addItem("Ошибка загрузки устройств")
            logging.error(f"Ошибка при загрузке устройств ввода: {str(e)}")

    def refreshDevices(self):
        self.loadOutputDevices()
        self.loadInputDevices()
        QMessageBox.information(self, 'Обновление', 'Список устройств обновлен')

    def loadSettings(self):
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.voice_speed.setValue(settings.get('voice_speed', 180))
                self.voice_volume.setValue(settings.get('voice_volume', 100))
                self.autostart.setChecked(settings.get('autostart', False))
                self.minimize_to_tray.setChecked(settings.get('minimize_to_tray', True))
                self.language.setCurrentText(settings.get('language', 'Русский'))
                self.continuous_recognition.setChecked(settings.get('continuous_recognition', True))
                self.noise_reduction.setChecked(settings.get('noise_reduction', True))

                # Загрузка настроек аудио устройств
                output_device = settings.get('output_device', {})
                input_device = settings.get('input_device', {})

                if output_device:
                    index = self.output_devices.findText(output_device.get('name', ''))
                    if index >= 0:
                        self.output_devices.setCurrentIndex(index)

                if input_device:
                    index = self.input_devices.findText(input_device.get('name', ''))
                    if index >= 0:
                        self.input_devices.setCurrentIndex(index)

        except FileNotFoundError:
            self.setDefaultSettings()

    def setDefaultSettings(self):
        self.voice_speed.setValue(180)
        self.voice_volume.setValue(100)
        self.autostart.setChecked(False)
        self.minimize_to_tray.setChecked(True)
        self.language.setCurrentText('Русский')
        self.continuous_recognition.setChecked(True)
        self.noise_reduction.setChecked(True)

    def chooseColor(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.parent.setStyleSheet(f'QMainWindow {{ background-color: {color.name()}; }}')

    def chooseFont(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.parent.setFont(font)

    def applySettings(self):
        settings = {
            'voice_speed': self.voice_speed.value(),
            'voice_volume': self.voice_volume.value(),
            'autostart': self.autostart.isChecked(),
            'minimize_to_tray': self.minimize_to_tray.isChecked(),
            'language': self.language.currentText(),
            'continuous_recognition': self.continuous_recognition.isChecked(),
            'noise_reduction': self.noise_reduction.isChecked(),
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

        self.parent.applySettings(settings)
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.loadCommands()
        self.initVoiceAssistant()
        self.initTrayIcon()
        self.setupLogging()
        self.loadSettings()

    def initUI(self):
        self.setWindowTitle('Голосовой ассистент')
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Верхняя панель с кнопками
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)

        self.status_label = QLabel("Статус: Готов к работе")
        self.status_label.setStyleSheet("""
                QLabel {
                    color: #2196F3;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 5px;
                    background: #E3F2FD;
                    border-radius: 4px;
                }
            """)
        top_layout.addWidget(self.status_label)

        settings_button = QPushButton('Настройки')
        settings_button.clicked.connect(self.showSettings)
        settings_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
        top_layout.addWidget(settings_button)

        layout.addWidget(top_panel)

        # Кнопки управления
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        self.start_button = QPushButton('Начать прослушивание')
        self.start_button.clicked.connect(self.startListening)
        self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)

        self.stop_button = QPushButton('Остановить')
        self.stop_button.clicked.connect(self.stopListening)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        layout.addWidget(control_panel)

        # Добавить текстовую панель ввода команд
        text_input_panel = QWidget()
        text_input_layout = QHBoxLayout(text_input_panel)

        self.command_input = CommandTextEdit(self)
        self.command_input.setMaximumHeight(50)
        self.command_input.setPlaceholderText("Введите команду здесь...")
        self.command_input.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
        """)

        send_button = QPushButton('Отправить')
        send_button.clicked.connect(self.sendTextCommand)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        text_input_layout.addWidget(self.command_input)
        text_input_layout.addWidget(send_button)
        layout.addWidget(text_input_panel)

        # Таблица команд
        commands_label = QLabel("Список доступных команд:")
        commands_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(commands_label)

        self.command_table = QTableWidget()
        self.command_table.setColumnCount(3)
        self.command_table.setHorizontalHeaderLabels(['Категория', 'Команда', 'Действие'])
        self.command_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.command_table)

        # Кнопки управления командами
        command_buttons = QWidget()
        command_buttons_layout = QHBoxLayout(command_buttons)

        add_command_btn = QPushButton('Добавить команду')
        add_command_btn.clicked.connect(self.addCommand)
        add_command_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)

        remove_command_btn = QPushButton('Удалить команду')
        remove_command_btn.clicked.connect(self.removeCommand)
        remove_command_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)

        command_buttons_layout.addWidget(add_command_btn)
        command_buttons_layout.addWidget(remove_command_btn)
        layout.addWidget(command_buttons)

        # Лог распознавания
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: white;
                    font-family: Consolas, Monaco, monospace;
                    padding: 5px;
                }
            """)
        layout.addWidget(self.log_text)

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
                self.applySettings(settings)
        except FileNotFoundError:
            pass

    def showSettings(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec_()

    def sendTextCommand(self):
        text = self.command_input.toPlainText().strip().lower()
        if text:
            self.logMessage(f"Введена команда: {text}")
            self.executeCommand(text)
            self.command_input.clear()

    def applySettings(self, settings):
        if hasattr(self, 'engine'):
            self.engine.setProperty('rate', settings['voice_speed'])
            self.engine.setProperty('volume', settings['voice_volume'] / 100)

            try:
                sd.default.device[1] = settings['output_device']['index']
            except Exception as e:
                logging.error(f"Ошибка при установке устройства вывода: {str(e)}")

        if hasattr(self, 'voice_thread'):
            if settings['language'] == 'Русский':
                self.voice_thread.recognition_language = 'ru-RU'
            else:
                self.voice_thread.recognition_language = 'en-US'

            try:
                input_device_index = settings['input_device']['index']
                sd.default.device[0] = input_device_index
                self.voice_thread.microphone = sr.Microphone(device_index=input_device_index)
            except Exception as e:
                logging.error(f"Ошибка при установке устройства ввода: {str(e)}")

            self.voice_thread.recognizer.dynamic_energy_threshold = settings['noise_reduction']

        if settings['autostart']:
            self.setupAutostart()
        else:
            self.removeAutostart()

        self.minimize_to_tray = settings['minimize_to_tray']
        self.logMessage("Настройки применены")

    def setupAutostart(self):
        key = reg.OpenKey(reg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, reg.KEY_SET_VALUE)
        reg.SetValueEx(key, "VoiceAssistant", 0, reg.REG_SZ, sys.argv[0])
        reg.CloseKey(key)

    def removeAutostart(self):
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run",
                                0, reg.KEY_SET_VALUE)
            reg.DeleteValue(key, "VoiceAssistant")
            reg.CloseKey(key)
        except WindowsError:
            pass

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

    # Установка общего стиля приложения
    app.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
                QLabel {
                    color: #333333;
                }
                QTableWidget {
                    background-color: white;
                    border: 1px solid #dddddd;
                    border-radius: 4px;
                }
                QTableWidget::item {
                    padding: 4px;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    padding: 4px;
                    border: 1px solid #dddddd;
                    font-weight: bold;
                }
                QTextEdit {
                    background-color: white;
                    border: 1px solid #dddddd;
                    border-radius: 4px;
                }
            """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()