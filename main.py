from cmu_graphics import *
from Sprites import *
from PIL import Image

import pyaudio
import numpy as np
from scipy.signal import find_peaks

class map:
    def __init__(self, objects = None):
        self.objects = []
        if(isinstance(objects, list)):
            self.objects = objects
    
    def addObject(self, object):
        if(isinstance(object, mapObject)):
            self.objects.append(object)

    def draw(self, app):
        for obj in self.objects:
            obj.draw(app)


class mapObject:
    def __init__(self, x, y, height = None, width = None, radius = None, color = None, shape = None):
        self.color = 'black' if color == None else color
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        self.radius = radius
        self.shape = shape
    
    def draw(self, app):
        if(self.shape == 'circle'):
            drawCircle(self.x + app.camX, self.y + app.camY, self.radius, fill=self.color)
        elif(self.shape == 'rect'):
            drawRect(self.x + app.camX, self.y + app.camY, self.width, self.height, fill=self.color)
        elif(self.shape == 'img'):
            pass

class Player:
    def __init__(self, x, y, width, height, sprite):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.sprite = Image.open(sprite)

    def draw(self):
        pass

# Function to map frequency to musical note
def frequency_to_note(freq):
    A4 = 440.0  # Frequency of A4
    C0 = A4 * 2**(-4.75)  # Frequency of C0
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    if freq == 0:
        return "No note"
    h = pythonRound(12 * np.log2(freq / C0))
    octave = h // 12
    n = h % 12
    return note_names[n] + str(octave)

def evaluatePitch(app):
    if(not app.isRecording):
        return
    
    data = app.stream.read(1024)
    framesData = np.frombuffer(data, dtype=np.int16)

    # Apply a window function
    window = np.hanning(len(framesData))
    framesData_windowed = framesData * window

    # Perform FFT
    freq_data = np.fft.fft(framesData_windowed)
    freq_magnitude = np.abs(freq_data)

    # Find peaks in the frequency magnitude
    peaks, properties = find_peaks(freq_magnitude[:len(freq_magnitude)//2], height=app.confidence_threshold, distance=5)

    if peaks.size > 0:
        peak_index = peaks[np.argmax(properties['peak_heights'])]
        peak_freq = abs(np.fft.fftfreq(len(framesData), 1/44100)[peak_index])
        note = frequency_to_note(peak_freq)
        app.freqList.pop(0)
        app.freqList.append(peak_freq)
        app.noteList.pop(0)
        app.noteList.append(note)
        print(f"Detected note: {app.note} (Frequency: {app.frequency} Hz)")
    
    if(app.freqList[0] == app.freqList[1] == app.freqList[2]):
        app.frequency = app.freqList[0]
    
    if(app.noteList[0] == app.noteList[1] == app.noteList[2]):
        app.note = app.noteList[0]

def onAppStart(app):

    app.audio = pyaudio.PyAudio()
    app.stream = app.audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    app.confidence_threshold = 2500  # Adjust this threshold based on testing

    app.isRecording = False
    app.message = 'Stopped'
    app.frequency = 0
    app.freqList = [0,0,0]
    app.noteList = ['C0', 'C0', 'C0']
    app.prevNote = 'C0'
    app.circleHeight = 0
    app.note = 'C0'

    app.color = 'black'

    app.readCommand = False
    app.prevCommand = None
    app.command = []
    app.commandTimer = 0

    app.spell = ''
    initializeSpells(app)
    initializeMap(app)
    app.player = Player(200, 200, 32, 32, sprite='Sprites/Mage-1.png')

def initializeSpells(app):
    app.spells = {'Dash':['blue'], 'Fireball':['red', 'green', 'red'], 'Thunder':['blue', 'red']}

def initializeMap(app):
    app.map = map()
    app.camX, app.camY = 0, 0
    app.map.addObject(mapObject(0, 0, shape='rect', width=50, height=50, color='maroon'))
    app.map.addObject(mapObject(50, 320, shape='circle', radius=20, color='purple'))

def onKeyPress(app, key):
    if(key == 'r'):
        app.isRecording = True
        app.message = "Recording..."
    elif(key == 's'):
        app.isRecording = False
        app.message = 'Stopped'
    elif(key == 'c'):
        if(app.readCommand):
            evaluateCommand(app)
        app.readCommand = not app.readCommand

def onKeyHold(app, keys):
    movePlayer(app, keys)

def movePlayer(app, keys):
    if('w' in keys):
        app.camY -= 3
    if('a' in keys):
        app.camX -= 3
    if('s' in keys):
        app.camY += 3
    if('d' in keys):
        app.camX += 3

def redrawAll(app):
    app.map.draw(app)
    app.player.draw()
    drawLabel(app.message, 200, 200, size = 20)
    drawLabel(app.frequency, 200, 240, size = 20)
    drawLabel(app.spell, 200, 300, size = 15)
    drawMeter(app)
    drawCommand(app)

def drawMeter(app):
    drawRect(5,5,20,40,fill='green')
    drawRect(5,45,20,40,fill='blue')
    drawRect(5,85,20,40,fill='red')
    yPos = 25
    if(app.color == 'blue'):
        yPos = 65
    elif(app.color == 'red'):
        yPos = 105
    drawCircle(15, yPos, 7, fill='black')

def drawCommand(app):

    curXPos = 20

    for command in app.command:
        drawCircle(curXPos, 300, 10, fill=command)
        curXPos += 8
    

def evaluateColor(app):
    app.color = 'black'
    if (app.note[:-1] == 'C' or app.note[:-1] == 'C#' or app.note[:-1] == 'F#' or app.note[:-1] == 'G'):
        app.color = 'red'
    elif (app.note[:-1] == 'D' or app.note[:-1] == 'D#' or app.note[:-1] == 'G#' or app.note[:-1] == 'A'):
        app.color = 'blue'
    elif (app.note[:-1] == 'E' or app.note[:-1] == 'F' or app.note[:-1] == 'A#' or app.note[:-1] == 'B'):
        app.color = 'green'

def evaluateCommand(app):
    foundSpell = False
    for spell in app.spells:
        if(app.spells[spell] == app.command):
            print(f"Cast {spell}")
            app.spell = spell
            foundSpell = True
    
    if(not foundSpell):
        app.spell = 'Spell Not found'

    app.commandTimer = 0

def readCommand(app):
    if(not app.readCommand):
        app.prevCommand = None

        if app.commandTimer < (1 * app.stepsPerSecond):
            app.commandTimer += 1
        else:
            app.spell = ''
            app.command = []
        return
    
    if(app.prevCommand == None):
        app.command = [app.color]
        app.prevCommand = app.color
    elif(app.prevCommand != app.color):
        app.command.append(app.color)
        app.prevCommand = app.color


def onStep(app):
    evaluatePitch(app)
    evaluateColor(app)
    readCommand(app)

def main():
    runApp()

main()