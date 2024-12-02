import time
import textwrap
import asyncio
from cmu_graphics import *
from Sprites import *
from PIL import Image
import random

import pyaudio
import numpy as np
from scipy.signal import find_peaks

from frequencyDetection import *
from colors import *
from spells import *
from animations import *

INSTRUCTIONS = ['Pay attention to these instructions.', 
                'Your objective as of right now is to discover all the color combinations for the spells around this apartment', 
                'You can do so by interacting with objects in this environment, which will give you clues as to what those color combinations are',
                'Pressing "E" on your keyboard will allow you to interact with these objects',
                'Use WASD to move around the map with your player',
                'You can give color commands with your voice. The higher your voice goes, the further up in the color meter it will go (top left corner of screen)',
                'It is recommended to sing in falsetto and around the note G4 to get more accurate voice detections',
                'If you are having difficulties with the voice detection, use the arrow keys to give your color input',
                'To begin recording your input, press "C", and to finish giving color input, press "C" again.',
                'Good Luck!']

def empty_function(app=None, a=None, b=None, c=None):
    pass

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

class Effect:
    def __init__(self, spritesheet, x, y, radius=None, areaColor=None):
        self.x = x
        self.y = y
        self.radius = radius
        self.curSprite = openAnimation(spritesheet[0], spritesheet[1])
        self.spriteIndex = 0
        self.spriteRate = None if(spritesheet == None) else spritesheet[2]
        self.spriteSize = None if(spritesheet == None) else (spritesheet[3], spritesheet[4])

        self.areaColor = areaColor

    def __eq__(self, other):
        if(isinstance(other, Effect)):
            return ((self.x, self.y) == (other.x, other.y) and self.curSprite == other.curSprite)
        return False

    def drawArea(self, app):
        if(self.radius != None):
            drawCircle(self.x - app.camX, self.y - app.camY, self.radius, border='black', opacity=40, fill=self.areaColor)

    def draw(self,app):
        if(self.curSprite[0][:-2] in EFFECTSPRITES):
            stopIndex = self.curSprite[self.spriteIndex].find('-')
            drawImage(f'./Sprites/{self.curSprite[self.spriteIndex][:stopIndex]}/{self.curSprite[self.spriteIndex]}.png', self.x - app.camX, self.y - app.camY, width=self.spriteSize[0], height=self.spriteSize[1], align='center')

    def updateAnimation(self, app):
        if(self.curSprite == None):
            return
        if(self.spriteIndex >= len(self.curSprite)-1):
            self.destroy(app)
            return
        rate = app.stepsPerSecond // self.spriteRate
        if(app.step % rate == 0):
            self.spriteIndex = (self.spriteIndex + 1) % len(self.curSprite)
    
    def destroy(self, app):
        index = listFind(app.map.effects, self)
        if(index != -1):
            app.map.effects.pop(index)

class map:
    def __init__(self, blockSize = app.width):
        self.blockSize = blockSize
        self.objects = []
        self.enemies = []
        self.projectiles = []
        self.objectBlocks = dict()
        self.enemyBlocks = dict()
        self.effects = []
        self.messages = []
        self.spawners = []
    
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
            enemy.setID(len(self.enemies))
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

    def addSpawner(self, spawner):
        if(isinstance(spawner, Spawner)):
            self.spawners.append(spawner)

    def addEffect(self, effect):
        if(isinstance(effect, Effect)):
            self.effects.append(effect)

    def addMessage(self, message):
        if(isinstance(message, Message)):
            self.messages.append(message)


    def addProjectile(self, projectile):
        self.projectiles.append(projectile)

    def moveProjectiles(self, app):
        for projectile in self.projectiles:
            projectile.move(app)
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
                return enemy
        return None

    def checkInteraction(self, app, other, radius):
        blocks = self.getBlocks(other.getEdges())
        hasCollided = False
        for block in blocks:
            for object in self.objectBlocks.get(block, []):
                for dx in {radius, -radius}:
                    if(object.checkCollision((other.x+dx, other.y, other.width, other.height))):
                        object.interact(app, other)
                        return (True, object)
                for dy in {radius, -radius}:
                    if(object.checkCollision((other.x, other.y+dy, other.width, other.height))):
                        object.interact(app, other)
                        return (True, object)
        return (False,)
                        
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
    
    def trackEnemies(self, app, secondsPassed):
        for enemy in self.enemies:
            enemy.moveAwayFromEnemies(app)
            enemy.trackZap(secondsPassed)
    
    def runSpawners(self, app, secondsPassed):
        for spawner in self.spawners:
            spawner.runSpawner(app, secondsPassed)

    def updateAnimations(self, app):
        for enemy in self.enemies:
            enemy.updateAnimation(app)
        for effect in self.effects:
            effect.updateAnimation(app)

    def changeMessages(self, delta):
        for message in self.messages:
            if(message.display):
                message.changeMessage(delta)

    def draw(self, app):

        drawImage('./Sprites/map.png', -app.camX, -app.camY) #Credit for spritesheet used to make the map: https://limezu.itch.io/

        for effect in self.effects:
            effect.drawArea(app)

        for obj in self.objects:
            obj.draw(app)

        app.player.draw(app)

        for enemy in self.enemies:
            enemy.draw(app)
        for projectile in self.projectiles:
            projectile.draw(app)
        for effect in self.effects:
            effect.draw(app)
        for message in self.messages:
            message.draw()


class MapObject:
    def __init__(self, x, y, height = None, width = None, radius = None, color = None, shape = None, sprite=None, interaction=empty_function):
        self.color = color
        self.x = x
        self.y = y
        self.radius = radius
        self.height = height
        self.width = width
        if(sprite != None):
            self.sprite = OBJECTSPRITES[sprite]
        if(radius != None):
            self.height = radius*2
            self.width = radius*2
        self.shape = shape
        self.edges = self.getEdges()
        self.interaction = interaction

    def __repr__(self):
        return f'<MapObject: {self.shape} at ({self.x}, {self.y})>'
    
    def draw(self, app):
        if(self.shape == 'circle'):
            if(self.color == None): return
            drawCircle(self.x - app.camX, self.y - app.camY, self.radius, fill=self.color, align='top-left')
        elif(self.shape == 'rect'):
            if(self.color == None): return
            drawRect(self.x - app.camX, self.y - app.camY, self.width, self.height, fill=self.color)
        elif(self.shape == 'image'):
            drawImage(f'./Sprites/objects/{self.sprite}.png', self.x-app.camX, self.y-app.camY, width=self.width, height=self.height)
    
    def getEdges(self):
        curList = [(self.x, self.y), (self.x + self.width, self.y), (self.x, self.y - self.height), (self.x + self.width, self.y + self.height)]
        for pos in range(self.x, self.x+self.width, 32):
            curList.extend([(pos, self.y), (pos, self.y+self.height)])
        for pos in range(self.y, self.y+self.height, 32):
            curList.extend([(self.x, pos), (self.x+self.width, pos)])
        return curList
        
            

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

    def interact(self, app, other):
        self.interaction(app)

    def stopInteraction(self, app):
        pass

class ReadableObject(MapObject):
    def __init__(self, x, y, height = None, width = None, radius = None, color = None, shape = None, sprite=None, interaction=empty_function, message=['']):
        super().__init__(x, y, height, width, radius, color, shape, sprite, interaction)
        self.message = message

    def interact(self, app, other):
        super().interact(app, other)
        app.textBox.displayMessage(self.message)

    def stopInteraction(self, app):
        app.textBox.stopDisplay()

class Enemy:
    def __init__(self, x, y, width, height, speed=2):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.width = width
        self.height = height
        self.edges = self.getEdges()
        self.sprites = ZOMBIESPRITES
        self.curSprite = openAnimation(self.sprites['idle'][0], self.sprites['idle'][1])
        self.curAnim = 'idle'
        self.spriteIndex = 0
        self.spriteRate = self.sprites['idle'][2]
        self.speed = speed
        self.visionLimit = 300
        self.visionBlocked = True
        self.confused = False
        self.health = 4
        self.id = None

        self.defaultColor = RGBZOMBIE
        self.color = [self.defaultColor[0], self.defaultColor[1], self.defaultColor[2]]

        self.zapped = False
        self.zapTimer = 0

    def setID(self, id):
        self.id = id

    def __eq__(self, other):
        if(isinstance(other, Enemy)):
            if(other.id == None or self.id == None):
                print(f'Either {other} or {self} have no id.')
                return False
            return self.id == other.id
        return False

    def draw(self, app):
        sprite = 'zombie_idle-1'
        if(0 <= self.spriteIndex < len(self.curSprite)):
            sprite = self.curSprite[self.spriteIndex]
        drawImage(f'./Sprites/{sprite[:-2]}/{sprite}.png', self.x - app.camX, self.y - app.camY, width=32, height=32)

    def updateAnimation(self, app):
        if(self.zapped):
            return
        rate = app.stepsPerSecond // self.spriteRate
        if(app.step % rate == 0):
            self.spriteIndex = (self.spriteIndex + 1) % len(self.curSprite)
        
        self.checkMovement()

    def checkMovement(self):
        if(self.dy > 0):
            anim = 'forwards'
        elif(self.dy < 0):
            anim = 'backwards'
        elif(self.dx > 0):
            anim = 'right'
        elif(self.dx < 0):
            anim = 'left'
        else:
            anim = 'idle'
        
        if(anim != self.curAnim):
            self.setAnimation(anim)
        

    def setAnimation(self, animation):
        self.curAnim = animation
        self.curSprite = openAnimation(self.sprites[animation][0], self.sprites[animation][1])
        self.spriteRate =  self.sprites[animation][2]

    def dealDamage(self, app, other):
        other.takeDamage(app, 1)
    
    def takeDamage(self, app, damage):
        self.health -= damage
        app.map.addEffect(Effect(('blood', 26, 30, 100, 100), self.x + self.width/2, self.y + self.height/2))
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
        return f'<Enemy w/ id={self.id} at {(self.x, self.y)}>'

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
            if(self.x <= x <= self.x+self.width):
                withinXBounds = True
        if(not withinXBounds):
            return False
        for y in {otherY, otherY + otherHeight}:
            if(self.y <= y <= self.y + self.height):
                self.collide(other)
                return True
            
    def collide(self, other):
        pass
        
    def move(self, app, dx, dy):

        self.dx, self.dy = dx, dy

        self.x += dx
        if(not(dx == 0)):
            if(app.map.checkAllObjectCollision(self) or self.checkCollisionWithPlayer(app)):
                self.x -= dx
                self.dx = 0

        self.y += dy
        if(not(dy == 0)):
            if(app.map.checkAllObjectCollision(self) or self.checkCollisionWithPlayer(app)):
                self.y -= dy
                self.dy = 0

    def moveAwayFromEnemies(self, app):
        collision = app.map.checkAllEnemiesCollision(self)
        if(self.id == collision.id):
            return
        change = (0, 0)
        speed = 1
        if(collision != None):
            if(self.x <= collision.x):
                self.x -= speed
                change = (change[0]-speed, change[1])
            else:
                self.x += speed
                change = (change[0] + speed, change[1])
            if(self.y <= collision.y):
                self.y -= speed
                change = (change[0], change[1] -speed)
            else:
                self.y += speed
                change = (change[0], change[1] + speed)
        if (app.map.checkAllObjectCollision(self) or self.checkCollisionWithPlayer(app)):
            self.x -= change[0]
            self.y -= change[0]

    def checkCollisionWithPlayer(self,app):

        if(self.checkCollision(app.player)):
            self.dealDamage(app, app.player)

    def canSee(self, app, other):
        self.dx = 0
        self.dy = 0
        tileSize = 32
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
    def __init__(self, x, y, width, height, sprites, speed=3):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.trueDx = 0
        self.trueDy = 0
        self.width = width
        self.height = height
        self.sprites = sprites
        self.curSprite = openAnimation(sprites['idle'][0], sprites['idle'][1])
        self.curAnim = 'idle'
        self.spriteIndex = 0
        self.spriteRate = sprites['idle'][2]
        self.speed = speed

        self.health = 10
        self.healthBarColor = 'red'
        self.isImmune = False

        self.immunityTimer = 0
        self.isDashing = False
        self.dashTimer = 0
        self.isInteracting = False
        self.interactionObject = None

    def draw(self, app):
        sprite = 'wizard_idle-1'
        if(0 <= self.spriteIndex < len(self.curSprite)):
            sprite = self.curSprite[self.spriteIndex]
        drawImage(f'./Sprites/{sprite[:-2]}/{sprite}.png', self.x - app.camX, self.y - app.camY)

    def updateAnimation(self, app):
        rate = app.stepsPerSecond // self.spriteRate
        if(app.step % rate == 0):
            self.spriteIndex = (self.spriteIndex + 1) % len(self.curSprite)
        
        self.checkMovement()

    def setAnimation(self, animation):
        self.curAnim = animation
        self.curSprite = openAnimation(self.sprites[animation][0], self.sprites[animation][1])
        self.spriteRate =  self.sprites[animation][2]


    def drawHealthBar(self, x, y, height):
        if(self.health >= 1):
            drawRect(x, y, self.health*10, height, fill=self.healthBarColor, borderWidth=4, border='black')

    def takeDamage(self, app, damage):
        if(not self.isImmune):
            if(self.health <= 0):
                self.death(app)
            else:
                self.health -= damage
                self.startImmunity()

    def startImmunity(self):
        self.isImmune = True
        self.immunityTimer = 2

    def checkImmunity(self, secondsPassed):
        self.immunityTimer -= secondsPassed
        if(self.healthBarColor == 'red'):
            self.healthBarColor = 'white'
        else:
            self.healthBarColor = 'red'
        if(self.immunityTimer <= 0):
            self.isImmune = False
            self.healthBarColor = 'red'

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
        app.map.projectiles.append(Fireball(self.x + self.width/2, self.y + self.height/2, self.dx*3, self.dy*3, Enemy))

    def thunder(self, app):
        for enemy in app.map.enemies:
            if(distance(self.x, self.y, enemy.x, enemy.y) < 90):
                enemy.takeDamage(app, 3)
                enemy.zap()
        
        app.map.addEffect(Effect(('thunder', 6, 3, 64, 64), self.x + self.width/2, self.y + self.height/2, radius=90, areaColor=rgb(138, 138, 255)))

    def heal(self, app):
        if(self.health < 10):
            self.health += 1

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

        self.trueDx = dx
        self.trueDy = dy
        
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
    
    def checkMovement(self):
        if(self.dy > 0):
            anim = 'forwards'
        elif(self.dy < 0):
            anim = 'backwards'
        elif(self.dx > 0):
            anim = 'right'
        elif(self.dx < 0):
            anim = 'left'
        else:
            anim = 'idle'
        
        if(anim != self.curAnim):
            self.setAnimation(anim)

    def interact(self, app):
        if(not self.isInteracting):
            interaction = app.map.checkInteraction(app, self, self.speed)
            if(interaction[0]):
                self.isInteracting = True
                self.interactionObject = interaction[1]
        else:
            self.interactionObject.stopInteraction(app)
            self.interactionObject = None
            self.isInteracting = False


    def __repr__(self):
        return f'<Player at {(self.x, self.y)}>'

    def getEdges(self):
        return [(self.x, self.y), (self.x + self.width, self.y), (self.x, self.y - self.height), (self.x + self.width, self.y + self.height)]
    
    def castSpell(self, app, spell):
        cast(app, self, spell)

    def death(self, app):
        gameover(app)

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

    def move(self, app):
        self.x += self.dx
        self.y += self.dy
        if(not ((-100 < self.x - app.camX < app.width + 100) and (-100 < self.y - app.camY < app.height + 100))):
            self.destroy(app)

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
        index = listFind(app.map.projectiles, self)
        if(index != -1):
            app.map.projectiles.pop(index)

class Fireball(Projectile):
    def __init__(self, x, y, dx, dy, targetType):
        super().__init__(x, y, dx, dy, targetType)
        self.radius = 5

    def enemyCollide(self, app, enemy):
        enemy.takeDamage(app, 5)
        self.destroy(app)

    def draw(self, app):
        drawCircle(self.x - app.camX, self.y-app.camY, self.radius, align='top-left', fill='red')

    def destroy(self, app):
        for localEnemy in app.map.enemies:
            dist = distance(self.x, self.y, localEnemy.x, localEnemy.y)
            if(dist < 50):
                localEnemy.takeDamage(app, int((1 - (dist/50))*5))
        app.map.addEffect(Effect(('explosion', 6, 3, 30, 30), self.x, self.y, 50, areaColor=rgb(255, 138, 138)))
        index = listFind(app.map.projectiles, self)
        if(index != -1):
            app.map.projectiles.pop(index)

class Message:
    def __init__(self, x, y, width, height, fontSize):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.messages = []
        self.messageIndex = 0
        self.lines = []
        self.display = False
        self.fontSize = fontSize

    def displayMessage(self, messages):
        self.display = True
        self.messages = messages
        self.messageIndex = 0
        self.lines = self.findLines(messages[self.messageIndex])

    def changeMessage(self, delta):
        if(0 <= self.messageIndex+delta < len(self.messages)):
            self.messageIndex += delta
            self.lines = self.findLines(self.messages[self.messageIndex])

    def stopDisplay(self):
        self.display = False
        self.message = ''
        self.messageIndex = 0
        self.lines = None
    
    def findLines(self, message):
        lines = []
        charsPerLine = int(self.width/10)
        pixels = self.x + len(message) * (self.fontSize/2.2)
        lineCount = len(message) // charsPerLine
        if(lineCount > 0):
            charsPerLine = len(message) // lineCount
        for i in range(lineCount):
            lines.append(message[i*charsPerLine:(i+1)*charsPerLine])
        lines.append(message[lineCount*charsPerLine:])
        return textwrap.fill(message, 60).splitlines()
    

    def draw(self):
        if(self.display):
            drawRect(self.x - 10, self.y - 10, self.width, self.height, border='black', borderWidth=4, fill='white', opacity=90)
            for i in range(len(self.lines)):
                drawLabel(self.lines[i], self.x, i*20 + self.y, size=self.fontSize, align='top-left')
            backText = ''
            nextText = 'press "E"'
            if(self.messageIndex > 0):backText = '<-- back'
            if(self.messageIndex < len(self.messages)-1): nextText = 'next -->'
            drawLabel(backText, self.x + 10, self.y + self.height - 30, align='top-left')
            drawLabel(nextText, self.x + self.width - 70, self.y + self.height - 30, align='top-left')

class Spawner:
    def __init__(self, x, y, spawnRate):
        self.x = x
        self.y = y
        self.spawnRate=spawnRate
        self.timer = 0

    def spawn(self, app):
        print('spawn')
        app.map.addEnemy(Enemy(self.x, self.y, 32, 32))

    def runSpawner(self, app, secondsPassed):
        self.timer += secondsPassed
        if(self.timer >= self.spawnRate):
            print('checkingSpawn')
            if(distance(app.player.x, app.player.y, self.x, self.y) < 160):
                print('distance too small')
                return
            self.timer = 0
            if len(app.map.enemies) < 10:
                self.spawn(app)

def gameover(app):
    app.gameover = True
    app.paused = True

def onAppStart(app):
    app.onStartScreen = True
    app.learnMode = False
    app.waveMode = False
    app.wave = 1
    app.waveTimer = 0
    reset(app)
    app.enemyPoints = [(160, 160), (128, 192), (32, 320), (96, 320), (160, 320),
                       (320, 96), (416, 96), (512, 96), (320, 160), (416, 160), (512, 160),
                       (320, 224), (416, 224), (512, 224), (320, 288), (416, 288), (512, 288),
                       (320, 416), (416, 416), (512, 416), (320, 544), (416, 544), (512, 544),
                       (48, 576), (176, 576), (48, 672), (176, 672), (48, 768), (176, 768),
                       (448, 768), (512, 768), (576, 768), (640, 768), (704, 768), 
                       (672, 224), (768, 224), (864, 224), (672, 288), (768, 288), (864, 288), 
                       (672, 352), (768, 352)]

def startLearnMode(app):
    app.onStartScreen = False
    app.waveMode = False
    app.learnMode = True
    initializeLearnMode(app)

def startWaveMode(app):
    app.onStartScreen = False
    app.learnMode = False
    app.waveMode = True
    app.wave = 1
    app.waveTimer = 30
    initializeWaveMode(app)

def goToStartScreen(app):
    app.onStartScreen = True
    app.learnMode = False
    app.waveMode = False

def reset(app):
    app.width = 800
    app.height = 800
    app.step = 0
    app.frameRate = 0
    app.startTime = time.time()
    app.paused = False
    app.gameover = False
    app.gameoverTimer = 5

    app.SPELLS = dict()
    app.SPELLCOOLDOWNS = dict()
    if(app.waveMode):
        app.SPELLS = {'Heal':['green'], 'Fireball':['red', 'green', 'red'], 'Thunder':['blue', 'red'], 'Dash':['blue']}
        app.SPELLCOOLDOWNS = {'Heal':2, 'Fireball':3, 'Thunder':5, 'Dash':1}

    app.audio = pyaudio.PyAudio()
    app.stream = app.audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    app.confidence_threshold = 2500  # Adjust this threshold based on testing

    app.isRecording = False
    app.noteDetected = False
    app.message = 'Stopped'
    app.frequency = 0
    app.freqList = [0,0,0]
    app.noteList = ['C0', 'C0', 'C0']
    app.prevNote = 'C0'
    app.note = 'C0'

    app.color = 'green'

    app.readCommand = False
    app.prevCommand = None
    app.command = []
    app.commandTimer = 0

    app.spell = ''
    app.spellCooldown = 0
    app.startingSpellCooldown = 0

    initializeMap(app)
    app.player = Player(app.width/2 - 16, app.height/2 - 16, 32, 32, sprites=PLAYERSPRITES, speed=3)

def setWave(app, wave):
    amountOfEnemies = wave*4
    app.waveTimer = 30*wave
    if(amountOfEnemies > 15): amountOfEnemies = 15
    for enemyIndex in range(amountOfEnemies):
        index = len(app.enemyPoints)
        while(index >= len(app.enemyPoints)):
            index = int(random.random()*len(app.enemyPoints))
        x, y = app.enemyPoints[index]
        app.map.addEnemy(Enemy(x,y,32, 32))

    if(wave > 4):
        for enemyIndex in range(wave-4):
            index = len(app.enemyPoints)
            while(index >= len(app.enemyPoints)):
                index = int(random.random()*len(app.enemyPoints))
            x, y = app.enemyPoints[index]
            spawnRate = 10 + (wave-4)*2
            if spawnRate > 60:
                spawnRate = 60
            print('add spaner')
            app.map.addSpawner(Spawner(x,y,spawnRate))

def checkWaveMode(app, secondsPassed):
    if(len(app.map.enemies) <= 0):
        app.wave += 1
        setWave(app, app.wave)
    app.waveTimer -= secondsPassed
    if(app.waveTimer <= 0):
        gameover(app)

def initializeMap(app):
    app.map = map(blockSize=64)
    app.camX, app.camY = 0, 0
    app.textBox = Message(20, 700, 500, 100, 16)
    app.map.addMessage(app.textBox)
    app.instructions = Message(100, 100, 600, 400, 16)
    app.map.addMessage(app.instructions)
    #app.instructions.displayMessage(INSTRUCTIONS)

    #Four Walls
    app.map.addObject(MapObject(0, 0, shape='rect', width=11, height=960))
    app.map.addObject(MapObject(0, 896, shape='rect', width=960, height=64))
    app.map.addObject(MapObject(949, 0, shape='rect', width=11, height=960))
    app.map.addObject(MapObject(0, 0, shape='rect', width=960, height=64))

    #Dividing Walls
    app.map.addObject(MapObject(276, 0, shape='rect', width=11, height=224))
    app.map.addObject(MapObject(0, 224, shape='rect', width=96, height=64))
    app.map.addObject(MapObject(160, 224, shape='rect', width=128, height=64))
    app.map.addObject(MapObject(0, 384, shape='rect', width=288, height=64))
    app.map.addObject(MapObject(256, 384, shape='rect', width=32, height=96))
    app.map.addObject(MapObject(256, 544, shape='rect', width=32, height=352))
    app.map.addObject(MapObject(608, 0, shape='rect', width=32, height=416))
    app.map.addObject(MapObject(608, 480, shape='rect', width=32, height=160))
    app.map.addObject(MapObject(288, 640, shape='rect', width=224, height=64))
    app.map.addObject(MapObject(576, 640, shape='rect', width=384, height=64))

    #Non-Interactible Furniture
        #Bathroom
    app.map.addObject(MapObject(332, 758, shape='rect',width=72, height=64))
        #Kitchen
    app.map.addObject(MapObject(678, 128, shape='rect', height=64, width=86))
    app.map.addObject(MapObject(804, 128, shape='rect', height=64, width=86))
    app.map.addObject(MapObject(840, 378, shape='rect', height=100, width=120))
    app.map.addObject(MapObject(712, 506, shape='rect', height=100, width=148))
        #Room 2
    app.map.addObject(MapObject(64, 510, shape='rect', height=32, width=64))
    app.map.addObject(MapObject(0, 608, shape='rect', height=50, width=32))
    app.map.addObject(MapObject(0, 672, shape='rect', height=50, width=32))
    app.map.addObject(MapObject(0, 736, shape='rect', height=50, width=32))
    app.map.addObject(MapObject(0, 800, shape='rect', height=50, width=32))
    app.map.addObject(MapObject(224, 608, shape='rect', height=50, width=32))
    app.map.addObject(MapObject(224, 672, shape='rect', height=50, width=32))
    app.map.addObject(MapObject(224, 736, shape='rect', height=50, width=32))
    app.map.addObject(MapObject(224, 800, shape='rect', height=50, width=32))

    #Bookshelves
        #Room 1
    app.map.addObject(ReadableObject(128,3,shape='rect',width=64,height=64, interaction=unlockDash, message=['Hey, here\'s an interesting book!','*Reading Secret of Dash*', 'You know, sometimes the answer lies in the very room you are in.', 'Look at all the colors in the room and find the most frequent color', 'The answer is simply 1 ball of that color']))
    app.map.addObject(ReadableObject(192,3,shape='rect',width=64,height=64, message=['Huh, nothing interesting around here']))
        #Room 2
    app.map.addObject(ReadableObject(192,398,shape='rect',width=64,height=53, message=['Aaaand done.', 'I read every single book in this bookshelf.', '(...)', 'This is sad.']))
    app.map.addObject(ReadableObject(96,622,shape='rect',width=64,height=50, message=['Hey, here\'s something interesting.', '*Reading The Lost Secret*', 'Are you in search of a secret? Huh? Are you?', 'Here\'s one: TV Contains more knowledge than books. It\'s a fact!',]))
    app.map.addObject(ReadableObject(96,750,shape='rect',width=64,height=50, message=['Hmmmmm... nothing interesting here.']))
        #Bathroom
    app.map.addObject(ReadableObject(672,664,shape='rect',width=64,height=45, message=['placeholder']))
    app.map.addObject(ReadableObject(640,664,shape='rect',width=32,height=45, message=['placeholder']))
    app.map.addObject(ReadableObject(736,664,shape='rect',width=32,height=45, message=['placeholder']))

    #Interactible Furniture
        #Bathroom
    app.map.addObject(ReadableObject(781,664,shape='rect',width=40,height=47, message=['placeholder']))
    app.map.addObject(ReadableObject(588,664,shape='rect',width=40,height=47, interaction=unlockFireball, message=['Oooooh', 'Hey, I look pretty good!', 'Is there anything else in this world as good looking as I am?', 'Mirror - "The paintings in the batroom look much better than you."', 'Did that mirror just talk?', 'Might as well check the paintings then.']))
        #Room 2
    app.map.addObject(ReadableObject(64,404,shape='rect',width=64,height=47, interaction=unlockHeal, message=['*TV Host starts talking', 'Very blue skies here in Pitt', 'I\'ve been told that this time of year, one green ball is all you need to heal yourself']))
        #Room 1
    app.map.addObject(ReadableObject(32, 40, shape='rect',width=96, height=56,message=['Hey, it\'s a blue sofa with 2 blue pillows', 'It looks pretty comfy...']))
    app.map.addObject(ReadableObject(32, 106, shape='rect',width=64, height=42,message=['It\'s nice to have a place where to put coffee on.', 'There\'s no space though. Who the hell places two blue lamps next to each other?']))
    app.map.addObject(ReadableObject(12, 148, shape='rect',width=32, height=60,message=['Nice to have a bit of green in the house.']))
    app.map.addObject(ReadableObject(224, 144, shape='rect',width=32, height=80,message=['It\'s a blue and a red lamp...', 'Why does the owner of this house love to waste space with lamps?']))
        #Kitchen
    app.map.addObject(ReadableObject(709, 511, shape='rect', height=28, width=19, interaction=unlockThunder, message=['Hey, looks like a couple was drinking here...', 'It\'s wierd they have two dinner tables only for a couple.', 'Maybe the tables are a clue!']))
    app.map.addObject(ReadableObject(840, 539, shape='rect', height=28, width=22, message=['Huh, another glass']))
    app.map.addObject(ReadableObject(838, 390, shape='rect', height=40, width=28, message=['Hmmmmmmmmmmm, I want that in my mouth right now!', 'Oh right, I don\'t have a mouth...']))

def initializeLearnMode(app):
    reset(app)
    app.map.addSpawner(Spawner(400, 400, 5))

def initializeWaveMode(app):
    app.wave = 1
    reset(app)
    setWave(app, app.wave)

def onKeyPress(app, key):
    if(key == 'escape'):
        app.paused = not app.paused
    if(key == 'left'):
        app.map.changeMessages(-1)
    if(key == 'right'):
        app.map.changeMessages(1)

#Functions that don't run when app is paused
    if(app.paused):
        pass
    elif(key == 'e'):
        app.player.interact(app)
    elif(key == 'r'):
        app.isRecording = not app.isRecording
        app.noteDetected = False
    elif(key == 'c'):
        if(app.spellCooldown <= 0):
            if(app.readCommand):
                evaluateCommand(app)
            app.readCommand = not app.readCommand
    elif(key == 'right'):
        app.color = 'red' 
    elif(key == 'left'):
        app.color = 'green'
    elif(key == 'up' or key == 'down'):
        app.color = 'blue'   

def onKeyHold(app, keys):
    if(app.paused):
        return
    app.player.move(app, keys)

def onMousePress(app, mouseX, mouseY):
    if(app.onStartScreen):
        if((app.width/2 - 200 < mouseX < app.width/2 + 200) and (375 < mouseY < 425)):
            startLearnMode(app)
        elif((app.width/2 - 200 < mouseX < app.width/2 + 200) and (475 < mouseY < 525)):
            startWaveMode(app)
    elif(app.gameover):
        if((app.width/2 - 200 < mouseX < app.width/2 + 200) and (375 < mouseY < 425)):
            if(app.waveMode): initializeWaveMode(app)
            elif(app.learnMode): initializeLearnMode(app)
        elif((app.width/2 - 200 < mouseX < app.width/2 + 200) and (475 < mouseY < 525)):
            goToStartScreen(app)

    print(32*(mouseX//32), 32*(mouseY//32))

def redrawAll(app):
    if(app.onStartScreen):
        drawStartScreen(app)
    else:
        app.map.draw(app)
        drawUI(app)
        if(app.waveMode):
            drawWaveTimer(app)
        if(app.gameover):
            drawGameOver(app)
        elif(app.paused):
            drawPauseScreen(app)

def drawWaveTimer(app):
    drawLabel(f'{int(app.waveTimer)}', 50, app.height - 50, size=20)

def drawStartScreen(app):
    drawLabel('Cast Your Heart Out!', app.width/2, 50, size=30, bold=True)
    drawRect(app.width/2, 400, 300, 50, fill='white', border='black', borderWidth=4, align = 'center')
    drawLabel('Learn', app.width/2, 400, align = 'center', size=20)
    drawRect(app.width/2, 500, 300, 50, fill='white', border='black', borderWidth=4, align = 'center')
    drawLabel('Wave Mode', app.width/2, 500, align = 'center', size=20)


def drawUI(app):
    drawLabel('Press "R" to open and close mic (bottom right). red --> open',400, 20, bold=True)
    drawLabel(f'frame rate: {app.frameRate}', app.width - 80, 20, bold=True)
    micColor = 'gray'
    if(app.isRecording): micColor = 'red'
    detectionColor=rgb(255, 100, 100)
    if(app.noteDetected):
        detectionColor='green'
    drawCircle(app.width-50, app.height-50, 5, fill=micColor)
    drawCircle(app.width-30, app.height-50, 5, fill=detectionColor)
    drawLabel(app.spell, 200, 300, size = 15)
    drawMeter(app)
    drawSpellCooldown(app, 50, 20, 100, 10)
    drawCommand(app)
    app.player.drawHealthBar(app.width-200, app.height - 50, 16)

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

def drawGameOver(app):
    drawRect(app.width/2, app.height/2, app.width - 80, app.height - 80, opacity=90, border='black', borderWidth=5, fill='white', align='center')
    drawLabel('GAME OVER', 200, 70, fill='red', size=30, bold=True)
    drawRect(app.width/2, 400, 300, 50, fill='white', border='black', borderWidth=4, align = 'center')
    drawLabel('Restart', app.width/2, 400, align = 'center', size=20)
    drawRect(app.width/2, 500, 300, 50, fill='white', border='black', borderWidth=4, align = 'center')
    drawLabel('Start Screen', app.width/2, 500, align = 'center', size=20)
    # drawLabel(f'Game will restart in {int(app.gameoverTimer)} seconds', app.width/2, app.height/2, size=20)

def drawPauseScreen(app):
    drawRect(app.width/2, app.height/2, app.width - 200, 100, opacity=90, border='black', borderWidth=5, fill='white', align='center')
    drawLabel('Pause', app.width/2, app.height/2 - 10, size=30, bold=True)
    drawLabel('Press "Esc" to return', app.width/2, app.height/2 + 30)

def onStep(app):
    if(app.onStartScreen):
        return
    # if(app.gameover):
    #     app.gameoverTimer -= 1/app.stepsPerSecond
    #     if(app.gameoverTimer < 0):
    #         reset(app)
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
    app.player.updateAnimation(app)
    app.map.updateAnimations(app)

    if(app.step % (app.stepsPerSecond//10) == 0):
        if(app.waveMode):
            checkWaveMode(app, (app.stepsPerSecond // 10) / app.stepsPerSecond)
        app.player.checkImmunity((app.stepsPerSecond // 10) / app.stepsPerSecond)
        app.player.trackDash((app.stepsPerSecond // 10) / app.stepsPerSecond)
        app.map.trackEnemies(app, (app.stepsPerSecond // 10) / app.stepsPerSecond)
        app.map.runSpawners(app, (app.stepsPerSecond // 10) / app.stepsPerSecond)
        trackSpellCooldown(app, (app.stepsPerSecond // 10) / app.stepsPerSecond)

def record(app):
    if(app.isRecording): 
        app.note = evaluatePitch(app, app.noteList)
        voiceColor = evaluateColor(app.note)
        if(voiceColor != None): app.color = voiceColor
    

def main():
    runApp()

main()