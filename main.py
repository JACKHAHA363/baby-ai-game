#!/usr/bin/env python3

import time
import sys
import threading
from optparse import OptionParser

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QLabel, QTextEdit, QFrame
from PyQt5.QtWidgets import QPushButton, QSlider, QHBoxLayout, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor

import gym
from gym_aigame.envs import AIGameEnv, Teacher
from model.training import selectAction

class AIGameWindow(QMainWindow):

    def __init__(self, env):
        super().__init__()
        self.initUI()

        # By default, manual stepping only
        self.fpsLimit = 0

        self.env = env
        self.lastObs = None

        self.resetEnv()

        self.stepTimer = QTimer()
        self.stepTimer.setInterval(0)
        self.stepTimer.setSingleShot(False)
        self.stepTimer.timeout.connect(self.stepClicked)

    def initUI(self):
        """Create and connect the UI elements"""

        self.resize(512, 512)
        self.setWindowTitle('Baby AI Game')

        # Full render view (large view)
        self.imgLabel = QLabel()
        self.imgLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        leftBox = QVBoxLayout()
        leftBox.addStretch(1)
        leftBox.addWidget(self.imgLabel)
        leftBox.addStretch(1)

        # Area on the right of the large view
        rightBox = self.createRightArea()

        # Arrange widgets horizontally
        hbox = QHBoxLayout()
        hbox.addLayout(leftBox)
        hbox.addLayout(rightBox)

        # Create a main widget for the window
        mainWidget = QWidget(self)
        self.setCentralWidget(mainWidget)
        mainWidget.setLayout(hbox)

        # Show the application window
        self.show()
        self.setFocus()

    def createRightArea(self):
        # Agent render view (partially observable)
        self.obsImgLabel = QLabel()
        self.obsImgLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        miniViewBox = QHBoxLayout()
        miniViewBox.addStretch(1)
        miniViewBox.addWidget(self.obsImgLabel)
        miniViewBox.addStretch(1)

        self.missionBox = QTextEdit()
        self.missionBox.setMinimumSize(500, 100)
        self.missionBox.textChanged.connect(self.missionEdit)

        self.adviceBox = QTextEdit()
        self.adviceBox.setMinimumSize(500, 100)
        self.adviceBox.textChanged.connect(self.adviceEdit)

        buttonBox = self.createButtons()

        self.stepsLabel = QLabel()
        self.stepsLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.stepsLabel.setAlignment(Qt.AlignCenter)
        self.stepsLabel.setMinimumSize(60, 10)
        resetBtn = QPushButton("Reset")
        resetBtn.clicked.connect(self.resetEnv)
        seedBtn = QPushButton("Seed")
        seedBtn.clicked.connect(self.reseedEnv)
        stepsBox = QHBoxLayout()
        stepsBox.addStretch(1)
        stepsBox.addWidget(QLabel("Steps remaining"))
        stepsBox.addWidget(self.stepsLabel)
        stepsBox.addWidget(resetBtn)
        stepsBox.addWidget(seedBtn)
        stepsBox.addStretch(1)

        hline2 = QFrame()
        hline2.setFrameShape(QFrame.HLine)
        hline2.setFrameShadow(QFrame.Sunken)

        # Stack everything up in a vetical layout
        vbox = QVBoxLayout()
        vbox.addLayout(miniViewBox)
        #vbox.addWidget(hline)
        vbox.addLayout(stepsBox)
        vbox.addWidget(hline2)
        vbox.addWidget(QLabel("General mission"))
        vbox.addWidget(self.missionBox)
        vbox.addWidget(QLabel("Contextual advice"))
        vbox.addWidget(self.adviceBox)
        vbox.addLayout(buttonBox)

        return vbox

    def createButtons(self):
        """Create the row of UI buttons"""

        stepButton = QPushButton("Step")
        stepButton.clicked.connect(self.stepClicked)

        minusButton = QPushButton("- Reward")
        minusButton.clicked.connect(self.minusReward)

        plusButton = QPushButton("+ Reward")
        plusButton.clicked.connect(self.plusReward)

        slider = QSlider(Qt.Horizontal, self)
        slider.setFocusPolicy(Qt.NoFocus)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(0)
        slider.valueChanged.connect(self.setFrameRate)

        self.fpsLabel = QLabel("Manual")
        self.fpsLabel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.fpsLabel.setAlignment(Qt.AlignCenter)
        self.fpsLabel.setMinimumSize(80, 10)

        # Assemble the buttons into a horizontal layout
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(stepButton)
        hbox.addWidget(slider)
        hbox.addWidget(self.fpsLabel)
        hbox.addStretch(1)
        hbox.addWidget(minusButton)
        hbox.addWidget(plusButton)
        hbox.addStretch(1)

        return hbox

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Left:
            self.stepEnv(AIGameEnv.ACTION_LEFT)
        elif e.key() == Qt.Key_Right:
            self.stepEnv(AIGameEnv.ACTION_RIGHT)
        elif e.key() == Qt.Key_Up:
            self.stepEnv(AIGameEnv.ACTION_FORWARD)
        elif e.key() == Qt.Key_Space:
            self.stepEnv(AIGameEnv.ACTION_TOGGLE)

        #elif e.key() == Qt.Key_PageUp:
        #    self.plusReward()
        #elif e.key() == Qt.Key_PageDown:
        #    self.minusReward()

    def mousePressEvent(self, event):
        """
        Clear the focus of the text boxes and buttons if somewhere
        else on the window is clicked
        """

        # Get the object currently in focus
        focused = QApplication.focusWidget()

        if isinstance(focused, (QPushButton, QTextEdit)):
            focused.clearFocus()

        QMainWindow.mousePressEvent(self, event)

    def missionEdit(self):
        # The agent will get the mission as an observation
        # before performing the next action
        text = self.missionBox.toPlainText()

    def adviceEdit(self):
        # The agent will get this advice as an observation
        # before performing the next action
        text = self.adviceBox.toPlainText()
        self.lastObs['advice'] = text

    def plusReward(self):
        print('+reward')
        self.env.setReward(1)

    def minusReward(self):
        print('-reward')
        self.env.setReward(-1)

    def stepClicked(self):
        self.stepEnv(action=None)

    def setFrameRate(self, value):
        """Set the frame rate limit. Zero for manual stepping."""

        print('Set frame rate: %s' % value)

        self.fpsLimit = int(value)

        if value == 0:
            self.fpsLabel.setText("Manual")
            self.stepTimer.stop()

        elif value == 100:
            self.fpsLabel.setText("Fastest")
            self.stepTimer.setInterval(0)
            self.stepTimer.start()

        else:
            self.fpsLabel.setText("%s FPS" % value)
            self.stepTimer.setInterval(int(1000 / self.fpsLimit))
            self.stepTimer.start()

    def resetEnv(self):
        obs = self.env.reset()

        if not isinstance(obs, dict):
            obs = { 'image': obs, 'advice': '', 'mission': '' }

        # If no mission is specified
        if obs['mission']:
            mission = obs['mission']
        else:
            mission = "Get to the green goal square"

        self.missionBox.setPlainText(mission)

        self.lastObs = obs

        self.showEnv(obs)

    def reseedEnv(self):
        import random
        seed = random.randint(0, 0xFFFFFFFF)
        self.env.seed(seed)
        self.resetEnv()

    def showEnv(self, obs):
        unwrapped = self.env.unwrapped

        # Render and display the environment
        pixmap = self.env.render(mode='pixmap')
        self.imgLabel.setPixmap(pixmap)

        # Render and display the agent's view
        image = obs['image']
        obsPixmap = unwrapped.getObsRender(image)
        self.obsImgLabel.setPixmap(obsPixmap)

        # Set the steps remaining displayadvice
        stepsRem = unwrapped.getStepsRemaining()
        self.stepsLabel.setText(str(stepsRem))

        advice = obs['advice']
        self.adviceBox.setPlainText(advice)

    def stepEnv(self, action=None):
        #print('stepEnv')
        #print('action=%s' % action)

        # If the environment doesn't supply a mission, get the
        # mission from the input text box
        if not hasattr(self.lastObs, 'mission'):
            text = self.missionBox.toPlainText()
            self.lastObs['mission'] = text

        # If no manual action was specified by the user
        if action == None:
            action = selectAction(self.lastObs)

        obs, reward, done, info = self.env.step(action)

        if not isinstance(obs, dict):
            obs = { 'image': obs, 'advice': '', 'mission': '' }

        self.showEnv(obs)
        self.lastObs = obs

        if done:
            self.resetEnv()

    def stepLoop(self):
        """Auto stepping loop, runs in its own thread"""

        print('stepLoop')

        while True:
            if self.fpsLimit == 0:
                time.sleep(0.1)
                continue

            if self.fpsLimit < 100:
                time.sleep(0.1)

            self.stepEnv()

def main(argv):

    parser = OptionParser()
    parser.add_option(
        "-e",
        "--env-name",
        dest="env",
        help="gym environment to load",
        default='AIGame-Multi-Room-N6-v0'
    )
    (options, args) = parser.parse_args()

    # Load the gym environment
    env = gym.make(options.env)
    #env = Teacher(env)

    # Create the application window
    app = QApplication(sys.argv)
    window = AIGameWindow(env)

    # Run the application
    sys.exit(app.exec_())

if __name__ == '__main__':
    main(sys.argv)
