SPELLS = {'Dash':['blue'], 'Fireball':['red', 'green', 'red'], 'Thunder':['blue', 'red']}
SPELLCOOLDOWNS = {'Dash': 1, 'Fireball':3, 'Thunder':5}

def evaluateCommand(app):
    foundSpell = 'Spell not found'
    for spell in SPELLS:
        if(SPELLS[spell] == app.command):
            foundSpell = spell
            app.player.castSpell(app, spell)
            break

    if(foundSpell == 'Spell not found'):
        app.spell = foundSpell

    app.commandTimer = app.stepsPerSecond
    app.command = []

def readCommand(app):

    if(app.commandTimer > 0):
        app.commandTimer -= 1
    else:
        app.spell = ''

    if(not app.readCommand):
        app.prevCommand = None
    elif(app.spellCooldown <= 0 and app.prevCommand == None):
        app.command = [app.color]
        app.prevCommand = app.color
    elif(app.spellCooldown <= 0 and app.prevCommand != app.color):
        app.command.append(app.color)
        app.prevCommand = app.color

def trackSpellCooldown(app, secondsPassed):
    if(app.spellCooldown > 0):
        app.spellCooldown -= secondsPassed


def cast(app, player, spell):
    if(app.spellCooldown > 0):
        return
    
    app.spell = spell
    app.spellCooldown = SPELLCOOLDOWNS[spell]
    app.startingSpellCooldown = app.spellCooldown

    if(spell == 'Dash'):
        player.dash()
        
