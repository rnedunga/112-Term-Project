import time
import asyncio
from cmu_graphics import *
from Sprites import *
from PIL import Image

import pyaudio
import numpy as np
from scipy.signal import find_peaks

from frequencyDetection import *
from colors import *
from spells import *
from animations import *

def distance(x1, y1, x2, y2):
    return ((x1-x2)**2 + (y1-y2)**2)**0.5

def roundInt(x1):
    base = int(x1)
    if(base == 0):
        base = 1
    if((x1%base) > 0.5):
        return base+1
    return int(x1)

def listFind(L, obj):
    index = -1
    try:
        index = L.index(obj)
    
    except ValueError:
        return -1
    return index

class map:
    def __init__(self, blockSize = app.width):
        self.blockSize = blockSize
        self.objects = []
        self.enemies = []
        self.projectiles = []
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

    def addProjectile(self, projectile):
        self.projectiles.append(projectile)

    def moveProjectiles(self, app):
        for projectile in self.projectiles:
            projectile.move()
            for enemy in self.enemies:
                projectile.checkCollision(app, enemy)
            blocks = self.getBlocks([(projectile.x, projectile.y), (projectile.x+(projectile.radius*2), projectile.y), (projectile.x, projectile.y+(projectile.radius)*2), (projectile.x+(projectile.radius*2), projectile.y+(projectile.radius*2))])
            for block in blocks:
                for object in self.objectBlocks.get(block, []):
                    projectile.checkCollision(app, object)

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
        return (int(blockX), int(blockY))

    def checkAllObjectCollision(self, other):
        blocks = self.getBlocks(other.getEdges())
        hasCollided = False
        for block in blocks:
            for object in self.objectBlocks.get(block, []):
                if(object.checkCollision(other)):
                    hasCollided = True

        return hasCollided
    
    def checkAllEnemiesCollision(self, other):
        for enemy in self.enemies:
            if(enemy.checkCollision(other)):
                return True
        return False

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
    
    def trackEnemies(self, secondsPassed):
        for enemy in self.enemies:
            enemy.trackZap(secondsPassed)

    def draw(self, app):
        for obj in self.objects:
            obj.draw(app)
        for enemy in self.enemies:
            enemy.draw(app)
        for projectile in self.projectiles:
            projectile.draw(app)


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

    def interact(self, other):
        pass

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
        self.health = 4

        self.defaultColor = RGBZOMBIE
        self.color = [self.defaultColor[0], self.defaultColor[1], self.defaultColor[2]]

        self.zapped = False
        self.zapTimer = 0

    def __eq__(self, other):
        if(isinstance(other, Enemy)):
            return (self.x, self.y) == (other.x, other.y)
        return False

    def draw(self, app):
        drawRect(self.x - app.camX, self.y - app.camY, self.width, self.height, fill=rgb(*self.color))

    def dealDamage(self, other):
        other.takeDamage(1)
    
    def takeDamage(self, app, damage):
        self.health -= damage
        if(self.health <= 0):
            self.death(app)
    
    def zap(self):
        self.zapped = True
        self.zapTimer = 3

    def trackZap(self, secondsPassed):
        if(self.zapped):
            if(self.zapTimer <= 0):
                self.zapped = False
            else:
                self.zapTimer -= secondsPassed
    
    def death(self, app):
        if self in app.map.enemies:
            app.map.enemies.remove(self)

    def interact(self, app):
        app.map.checkInteraction(self, self.speed)

    def __repr__(self):
        return f'<Enemy at {(self.x, self.y)}>'

    def getEdges(self):
        return [(self.x, self.y), (self.x + self.width, self.y), (self.x, self.y - self.height), (self.x + self.width, self.y + self.height)]

    def followPlayer(self, app):

        if(self.zapped):
            return

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
        self.move(app, dx, dy)

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
        
    def move(self, app, dx, dy):
        self.x += dx
        if(not(dx == 0)):
            if(app.map.checkAllObjectCollision(self) or self.checkCollisionWithPlayer(app) or app.map.checkAllEnemiesCollision(self)):
                self.x -= dx

        self.y += dy
        if(not(dy == 0)):
            if(app.map.checkAllObjectCollision(self) or self.checkCollisionWithPlayer(app) or app.map.checkAllEnemiesCollision(self)):
                self.y -= dy

    def checkCollisionWithPlayer(self,app):

        if(self.checkCollision(app.player)):
            self.dealDamage(app.player)

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
                    ratio = 0
                    if(dir[0] != 0):
                        ratio = abs(dir[1] / dir[0])
                    curCheck = (curCheck[0] + (normX*distToX), curCheck[1] + normY * (distToX * ratio))
                else:
                    ratio = 0
                    if(dir[1] != 0):
                        ratio = abs(dir[0] / dir[1])
                    curCheck = (curCheck[0] + normX*(distToY * ratio), curCheck[1] + (normY*distToY))

                
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
        self.dx = 0
        self.dy = 0
        self.width = width
        self.height = height
        self.sprite = sprite
        # self.sprites = sprites
        # self.curSprite = openAnimation(sprites['idle'][0], sprites['idle'][1])
        # self.spriteIndex = 0
        # self.spriteRate = 5
        self.speed = speed
        self.health = 10
        self.isImmune = False
        self.immunityTimer = 0
        self.isDashing = False
        self.dashTimer = 0

    def draw(self, app):
        # sprite = self.curSprite[app.step % len(self.curSprite)]
        drawImage(f'./Sprites/{self.sprite}', self.x - app.camX, self.y - app.camY)

    def drawHealthBar(self, x, y, height):
        if(self.health >= 1):
            drawRect(x, y, self.health*10, height, fill='red', borderWidth=4, border='black')

    def takeDamage(self, damage):
        if(not self.isImmune):
            if(self.health <= 0):
                self.death()
            else:
                self.health -= damage
                self.startImmunity()

    def startImmunity(self):
        self.isImmune = True
        self.immunityTimer = 0

    def checkImmunity(self, secondsPassed):
        self.immunityTimer += secondsPassed
        if(self.immunityTimer >= 2):
            self.isImmune = False

    def dash(self):
        self.speed *= 2
        self.dashTimer = 0.5
        self.isDashing = True

    def trackDash(self, secondsPassed):
        if(self.isDashing):
            self.dashTimer -= secondsPassed
            if(self.dashTimer < 0):
                self.isDashing = False
                self.speed //= 2

    def fireball(self, app):
        app.map.projectiles.append(Fireball(self.x, self.y, self.dx*3, self.dy*3, Enemy))

    def thunder(self, app):
        for enemy in app.map.enemies:
            if(distance(self.x, self.y, enemy.x, enemy.y) < 90):
                enemy.takeDamage(app, 1)
                enemy.zap()


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
        
        if(not(dx == 0 and dy == 0)):
            self.dx = dx
            self.dy = dy

        self.x += dx
        app.camX += dx

        if(not(dx == 0)):
            if(app.map.checkAllObjectCollision(self)):
                app.camX -= dx
                self.x -= dx

        self.y += dy
        app.camY += dy

        if(not(dy == 0)):
            if(app.map.checkAllObjectCollision(self)):
                app.camY -= dy
                self.y -= dy

    def interact(self, app):
        app.map.checkInteraction(self, self.speed)

    def __repr__(self):
        return f'<Player at {(self.x, self.y)}>'

    def getEdges(self):
        return [(self.x, self.y), (self.x + self.width, self.y), (self.x, self.y - self.height), (self.x + self.width, self.y + self.height)]
    
    def castSpell(self, app, spell):
        cast(app, self, spell)

    def death(self):
        print("Gameover")

class Projectile:
    def __init__(self, x, y, dx, dy, targetType):
        self.x = x
        self.y = y
        self.radius = 3
        self.dx = dx
        self.dy = dy
        self.targetType = targetType

    def __repr__(self):
        return f'<Projectile at {(self.x, self.y)}>'

    def __eq__(self, other):
        if(isinstance(other, Projectile)):
            return (self.x, self.y, self.radius) == (other.x, other.y, other.radius)
        return False
    
    def draw(self, app):
        drawCircle(self.x - app.camX, self.y-app.camY, self.radius, align='top-left', fill='black')

    def move(self):
        self.x += self.dx
        self.y += self.dy

    def checkCollision(self, app, other):

        hasCollided = False
        if(isinstance(other, MapObject)):
            if(other.checkCollision((self.x, self.y, self.radius, self.radius))):
                hasCollided = True
                self.objectCollide(app, other)
        elif(isinstance(other, Enemy)):
            if(other.checkCollision((self.x, self.y, self.radius, self.radius))):
                hasCollided = True
                self.enemyCollide(app, other)
                
        return hasCollided

    def objectCollide(self, app, object):
        self.destroy(app)

    def enemyCollide(self, app, enemy):
        enemy.takeDamage(app, 5)
        self.destroy(app)

    def destroy(self, app):
        print("destroy Projectile")
        index = listFind(app.map.projectiles, self)
        if(index != -1):
            print("Found Self")
            print(self, app.map.projectiles[index])
            app.map.projectiles.pop(index)

class Fireball(Projectile):
    def __init__(self, x, y, dx, dy, targetType):
        super().__init__(x, y, dx, dy, targetType)
        self.radius = 5

    def enemyCollide(self, app, enemy):
        enemy.takeDamage(app, 3)
        for localEnemy in app.map.enemies:
            if(distance(self.x, self.y, localEnemy.x, localEnemy.y) < 100):
                localEnemy.takeDamage(app, 2)
        self.destroy(app)

    def draw(self, app):
        drawCircle(self.x - app.camX, self.y-app.camY, self.radius, align='top-left', fill='red')

def onAppStart(app):

    app.width = 800
    app.height = 800
    app.step = 0
    app.frameRate = 0
    app.startTime = time.time()
    app.paused = True

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
    app.spellCooldown = 0
    app.startingSpellCooldown = 0

    initializeMap(app)
    app.player = Player(app.width/2 - 16, app.height/2 - 16, 32, 32, sprite='Mage-1.png', speed=3)

def initializeMap(app):
    app.map = map()
    app.camX, app.camY = 0, 0
    app.map.addObject(ReadableObject(0, 0, shape='rect', width=64, height=64, color='maroon', message="I'm a bookshelf!"))
    app.map.addObject(MapObject(50, 320, shape='circle', radius=20, color='purple'))
    app.map.addEnemy(Enemy(300, 300, 32, 32, sprite='', speed=2))
    app.map.addEnemy(Enemy(200, 200, 32, 32, sprite='', speed=2))
    app.map.addEnemy(Enemy(100, 100, 32, 32, sprite='', speed=2))
    app.map.addEnemy(Enemy(0, 0, 32, 32, sprite='', speed=2))


def onKeyPress(app, key):
    if(key == 'r'):
        app.isRecording = not app.isRecording
    elif(key == 'c'):
        if(app.spellCooldown <= 0):
            if(app.readCommand):
                evaluateCommand(app)
            app.readCommand = not app.readCommand
    elif(key == 'e'):
        app.player.interact(app)
    elif(key == 'escape'):
        app.paused = not app.paused

# For debugging:

    elif(key == 'l'):
        takeStep(app)
    elif(key == 'f'):
        app.player.fireball(app)
    elif(key == 't'):
        app.player.thunder(app)

def onKeyHold(app, keys):
    app.player.move(app, keys)

def redrawAll(app):
    drawLabel('Press "R" to open and close mic (bottom right). red --> open',400, 20)
    drawLabel(f'frame rate: {app.frameRate}', app.width - 80, 20)
    micColor = 'gray'
    if(app.isRecording): micColor = 'red'
    drawCircle(750, 750, 5, fill=micColor)
    app.map.draw(app)
    app.player.draw(app)
    #drawLabel(app.message, 200, 40, size = 20)
    #drawLabel(app.frequency, 200, 240, size = 20)
    drawLabel(app.spell, 200, 300, size = 15)
    drawMeter(app)
    drawSpellCooldown(app, 50, 20, 100, 10)
    drawCommand(app)
    app.player.drawHealthBar(600, 750, 20)

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

def drawSpellCooldown(app, x, y, width, height):
    drawRect(x, y, width, height, fill='white')
    if(app.spellCooldown > 0.1):
        drawRect(x, y, (app.spellCooldown/app.startingSpellCooldown)*width, height, fill='lightBlue')
    drawRect(x, y, width, height, fill=None, border='black', borderWidth=3)

def drawCommand(app):

    curXPos = 20

    for command in app.command:
        drawCircle(curXPos, 300, 10, fill=command)
        curXPos += 8


def onStep(app):
    if(not app.paused):
        takeStep(app)
    if(app.step % app.stepsPerSecond == 0):
        curTime = time.time()
        app.frameRate = int(app.stepsPerSecond/(curTime-app.startTime))
        app.startTime = curTime


def takeStep(app):
    app.step += 1
    record(app)
    readCommand(app)
    app.map.enemiesFollowPlayer(app)
    app.map.moveProjectiles(app)

    if(app.step % (app.stepsPerSecond//10) == 0):
        app.player.checkImmunity((app.stepsPerSecond // 10) / app.stepsPerSecond)
        app.player.trackDash((app.stepsPerSecond // 10) / app.stepsPerSecond)
        app.map.trackEnemies((app.stepsPerSecond // 10) / app.stepsPerSecond)
        trackSpellCooldown(app, (app.stepsPerSecond // 10) / app.stepsPerSecond)

    

def record(app):
    if(app.isRecording): 
        app.note = evaluatePitch(app, app.noteList)
        voiceColor = evaluateColor(app.note)
        if(voiceColor != None): app.color = voiceColor
    

def main():
    runApp()

main()