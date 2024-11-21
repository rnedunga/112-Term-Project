from cmu_graphics import *
from Sprites import *
from PIL import Image

import pyaudio
import numpy as np
from scipy.signal import find_peaks

def distance(x1, y1, x2, y2):
    return ((x1-x2)**2 + (y1-y2)**2)**0.5

def roundInt(x1):
    base = int(x1)
    if(base == 0):
        base = 1
    if((x1%base) > 0.5):
        return base+1
    return int(x1)

class map:
    def __init__(self, blockSize = app.width):
        self.blockSize = blockSize
        self.objects = []
        self.enemies = []
        self.objectBlocks = dict()
        self.enemyBlocks = dict()
    
    def addObject(self, object):
        if(isinstance(object, MapObject)):
            self.objects.append(object)
            edges = object.getEdges()
            blocks = set()
            for edge in edges:
                x,y = edge
                block = self.getBlock(x,y)
                if(block not in blocks):
                    blocks.add(block)
                    self.objectBlocks[block] = self.objectBlocks.get(block, set())
                    self.objectBlocks[block].add(object)
            #print(self.objectBlocks)

    def addEnemy(self, enemy):
        if(isinstance(enemy, Enemy)):
            self.enemies.append(enemy)
            edges = enemy.getEdges()
            blocks = set()
            for edge in edges:
                x,y = edge
                block = self.getBlock(x,y)
                if(block not in blocks):
                    blocks.add(block)
                    self.enemyBlocks[block] = self.enemyBlocks.get(block, set())
                    self.enemyBlocks[block].add(object)
            #print(self.enemyBlocks)

    def getBlocks(self, edgeList):
        blockList = set()
        for edge in edgeList:
            x,y = edge
            blockList.add(self.getBlock(x,y))
        return blockList
            
    def getBlock(self, x, y):
        signX = 1
        signY = 1
        if(x < 0):
            signX = -1
        if(y < 0):
            signY = -1
        x = abs(x)
        y = abs(y)
        blockX = signX * ((x // self.blockSize) + 1)
        blockY = signY * ((y // self.blockSize) + 1)
        return (blockX, blockY)

    def checkAllObjectCollision(self, other):
        blocks = self.getBlocks(other.getEdges())
        hasCollided = False
        for block in blocks:
            #print(self.objectBlocks.get(block, []), end='')
            for object in self.objectBlocks.get(block, []):
                if(object.checkCollision(other)):
                    hasCollided = True
        #print()
        return hasCollided

    def checkInteraction(self, other, radius):
        blocks = self.getBlocks(other.getEdges())
        hasCollided = False
        for block in blocks:
            for object in self.objectBlocks.get(block, []):
                for dx in {radius, -radius}:
                    if(object.checkCollision((other.x+dx, other.y, other.width, other.height))):
                        object.interact(other)
                        return True
                for dy in {radius, -radius}:
                    if(object.checkCollision((other.x, other.y+dy, other.width, other.height))):
                        object.interact(other)
                        return True
                        
    def checkHit(self, other, radius):
        otherX, otherY, otherWidth, otherHeight = other
        blocks = self.getBlocks([(otherX, otherY)])
        hasCollided = False
        for block in blocks:
            for object in self.objectBlocks.get(block, []):
                for dx in {radius, -radius}:
                    if(object.checkCollision((otherX+dx, otherY, otherWidth, otherHeight))):
                        return True
                for dy in {radius, -radius}:
                    if(object.checkCollision((otherX, otherY+dy, otherWidth, otherHeight))):
                        return True

    def enemiesFollowPlayer(self, app):
        for enemy in self.enemies:
            enemy.followPlayer(app)

    def draw(self, app):
        for obj in self.objects:
            obj.draw(app)
        for enemy in self.enemies:
            enemy.draw(app)


class MapObject:
    def __init__(self, x, y, height = None, width = None, radius = None, color = None, shape = None):
        self.color = 'black' if color == None else color
        self.x = x
        self.y = y
        self.radius = radius
        self.height = height
        self.width = width
        if(radius != None):
            self.height = radius*2
            self.width = radius*2
        self.shape = shape

    def __repr__(self):
        return f'<MapObject: {self.shape} at ({self.x}, {self.y})>'
    
    def draw(self, app):
        if(self.shape == 'circle'):
            drawCircle(self.x - app.camX, self.y - app.camY, self.radius, fill=self.color, align='top-left')
        elif(self.shape == 'rect'):
            drawRect(self.x - app.camX, self.y - app.camY, self.width, self.height, fill=self.color)
        elif(self.shape == 'img'):
            pass
    
    def getEdges(self):
        return [(self.x, self.y), (self.x + self.width, self.y), (self.x, self.y - self.height), (self.x + self.width, self.y + self.height)]

    def checkCollision(self, other):
        if(isinstance(other, tuple)):
            otherX, otherY, otherWidth, otherHeight = other
        else:
            otherX, otherY, otherWidth, otherHeight = other.x, other.y, other.width, other.height

        withinXBounds = False
        for x in {otherX, otherX + otherWidth}:
            if(self.x < x < self.x+self.width):
                withinXBounds = True
        if(not withinXBounds):
            return False
        for y in {otherY, otherY + otherHeight}:
            if(self.y < y < self.y + self.height):
                self.collide(other)
                return True

    def collide(self, other):
        pass
        #print(f'{self} collided w/ {other}')

    def interact(self, other):
        pass
        #print(f'<{other} interacted w/ {self}')

class ReadableObject(MapObject):
    def __init__(self, x, y, height = None, width = None, radius = None, color = None, shape = None, message=''):
        super().__init__(x, y, height, width, radius, color, shape)
        self.message = message

    def interact(self, other):
        print(self.message)

class Enemy:
    def __init__(self, x, y, width, height, sprite, speed=2):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.sprite = sprite
        self.speed = speed
        self.visionLimit = 300
        self.visionBlocked = False

    def draw(self, app):
        drawRect(self.x - app.camX, self.y - app.camY, self.width, self.height, fill='lightGreen')

    def interact(self, app):
        app.map.checkInteraction(self, self.speed)

    def __repr__(self):
        return f'<Enemy at {(self.x, self.y)}>'

    def getEdges(self):
        return [(self.x, self.y), (self.x + self.width, self.y), (self.x, self.y - self.height), (self.x + self.width, self.y + self.height)]

    def followPlayer(self, app):
        if(app.step % 30 == 0):
            if(self.canSee(app, app.player)):
                self.visionBlocked = False
            else:
                self.visionBlocked = True

        if(self.visionBlocked):
            return

        target = (app.player.x, app.player.y)
        distanceToTarget = ((target[0]-self.x)**2 + (target[1]-self.y)**2)**0.5
        dx = (self.speed/distanceToTarget) * (target[0]-self.x)
        dy = (self.speed/distanceToTarget) * (target[1]-self.y)
        self.move(dx, dy)
        
    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def canSee(self, app, other):
        tileSize = 64
        selfX, selfY = self.x + self.width/2, self.y + self.height/2
        otherX, otherY = other.x + other.width/2, other.y + other.height/2
        distX = otherX - selfX
        distY = otherY - selfY
        dist = distance(selfX, selfY, otherX, otherY)
        if(dist <= 1):
            return True
        dir = (distX/dist, distY/dist)

        normX, normY = 1,1
        if(otherX < selfX): normX = -1
        if(otherY < selfY): normY = -1

        if(dist < self.visionLimit):
            curCheck = (selfX, selfY)
            while True:
                distToX = normX*curCheck[0] % tileSize
                distToY = normY*curCheck[1] % tileSize

                distToX = tileSize - distToX
                distToY = tileSize - distToY

                distXToEdge = distToX
                distYToEdge = distToY

                if(distX != 0):
                    distXToEdge = distance(0, 0, distToX, distToX*(distY/distX))
                if(distY != 0):
                    distYToEdge = distance(0, 0, distToY*(distX/distY), distToY)
                
                if distXToEdge < distYToEdge:
                    curCheck = (curCheck[0] + (normX*distToX), curCheck[1] + normY * (distToX * abs(dir[1] / dir[0])))
                else:
                    curCheck = (curCheck[0] + normX*(distToY * abs(dir[0] / dir[1])), curCheck[1] + (normY*distToY))

                
                curCheck = (roundInt(curCheck[0]), roundInt(curCheck[1]))

                if(distance(self.x, self.y, curCheck[0], curCheck[1]) > dist):
                    return True
                if app.map.checkHit((curCheck[0], curCheck[1], 1, 1), 1):
                    return False
        else:
            return False
                    


            

class Player:
    def __init__(self, x, y, width, height, sprite, speed=3):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.sprite = sprite
        self.speed = speed

    def draw(self, app):
        drawImage(self.sprite, self.x - app.camX, self.y - app.camY)
        #drawRect(self.x - app.camX, self.y - app.camY, self.width, self.height, fill='black')

    def move(self, app, keys):
        dx = 0
        dy = 0
        if('w' in keys):
            dy -= self.speed
        if('a' in keys):
            dx -= self.speed
        if('s' in keys):
            dy += self.speed
        if('d' in keys):
            dx += self.speed

        app.camX += dx
        app.camY += dy
        self.x += dx
        self.y += dy

        if(not(dx == 0 and dy == 0)):
            if(app.map.checkAllObjectCollision(self)):
                app.camX -= dx
                app.camY -= dy
                self.x -= dx
                self.y -= dy

    def interact(self, app):
        app.map.checkInteraction(self, self.speed)

    def __repr__(self):
        return f'<Player at {(self.x, self.y)}>'

    def getEdges(self):
        return [(self.x, self.y), (self.x + self.width, self.y), (self.x, self.y - self.height), (self.x + self.width, self.y + self.height)]

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
    
    data = app.stream.read(1024) #Chat GPT
    framesData = np.frombuffer(data, dtype=np.int16) #Chat GPT

    # Apply a window function
    window = np.hanning(len(framesData)) #Chat GPT
    framesData_windowed = framesData * window #Chat GPT

    # Perform FFT
    freq_data = np.fft.fft(framesData_windowed) #Chat GPT
    freq_magnitude = np.abs(freq_data) #Chat GPT

    # Find peaks in the frequency magnitude
    peaks, properties = find_peaks(freq_magnitude[:len(freq_magnitude)//2], height=app.confidence_threshold, distance=5) #Chat GPT

    if peaks.size > 0:
        peak_index = peaks[np.argmax(properties['peak_heights'])] #Chat GPT
        peak_freq = abs(np.fft.fftfreq(len(framesData), 1/44100)[peak_index]) #Chat GPT
        note = frequency_to_note(peak_freq)
        app.freqList.pop(0)
        app.freqList.append(peak_freq)
        app.noteList.pop(0)
        app.noteList.append(note)
        #print(f"Detected note: {app.note} (Frequency: {app.frequency} Hz)")
    
    if(app.freqList[0] == app.freqList[1] == app.freqList[2]):
        app.frequency = app.freqList[0]
    
    if(app.noteList[0] == app.noteList[1] == app.noteList[2]):
        app.note = app.noteList[0]

def onAppStart(app):

    app.width = 800
    app.height = 800
    app.step = 0
    app.stepMode = True

    app.audio = pyaudio.PyAudio()
    app.stream = app.audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    app.confidence_threshold = 2500  # Adjust this threshold based on testing

    app.isRecording = False
    app.message = 'Stopped'
    app.frequency = 0
    app.freqList = [0,0,0]
    app.noteList = ['C0', 'C0', 'C0']
    app.prevNote = 'C0'
    app.note = 'C0'

    app.color = 'black'

    app.readCommand = False
    app.prevCommand = None
    app.command = []
    app.commandTimer = 0

    app.spell = ''
    initializeSpells(app)
    initializeMap(app)
    app.player = Player(app.width/2 - 16, app.height/2 - 16, 32, 32, sprite='C:\CMU/Classes/15112/TermProject/Sprites/Mage-1.png', speed=3)

def initializeSpells(app):
    app.spells = {'Dash':['blue'], 'Fireball':['red', 'green', 'red'], 'Thunder':['blue', 'red']}

def initializeMap(app):
    app.map = map()
    app.camX, app.camY = 0, 0
    app.map.addObject(ReadableObject(0, 0, shape='rect', width=50, height=50, color='maroon', message="I'm a bookshelf!"))
    app.map.addObject(MapObject(50, 320, shape='circle', radius=20, color='purple'))
    app.map.addEnemy(Enemy(300, 300, 32, 32, sprite='', speed=2))
    app.map.addEnemy(Enemy(200, 200, 32, 32, sprite='', speed=2))
    app.map.addEnemy(Enemy(100, 100, 32, 32, sprite='', speed=2))
    app.map.addEnemy(Enemy(0, 0, 32, 32, sprite='', speed=2))


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
    elif(key == 'e'):
        app.player.interact(app)
    elif(key == 'p'):
        app.stepMode = not app.stepMode
    elif(key == 'l'):
        takeStep(app)

def onKeyHold(app, keys):
    app.player.move(app, keys)

def redrawAll(app):
    drawLabel('Press "R" to open mic and "S" to close',400, 20)
    app.map.draw(app)
    app.player.draw(app)
    #drawLabel(app.message, 200, 40, size = 20)
    #drawLabel(app.frequency, 200, 240, size = 20)
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
    if(not app.stepMode):
        takeStep(app)

def takeStep(app):
    app.step += 1
    evaluatePitch(app)
    evaluateColor(app)
    readCommand(app)
    app.map.enemiesFollowPlayer(app)
    

def main():
    runApp()

main()