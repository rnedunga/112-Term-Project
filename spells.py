def unlockDash(app):
    app.SPELLS['Dash'] = ['blue']
    app.SPELLCOOLDOWNS['Dash'] = 1

def unlockFireball(app):
    app.SPELLS['Fireball'] = ['red', 'green', 'red']
    app.SPELLCOOLDOWNS['Fireball'] = 5

def unlockFreeze(app):
    app.SPELLS['Freeze'] = ['blue', 'red']
    app.SPELLCOOLDOWNS['Freeze'] = 2

def unlockHeal(app):
    app.SPELLS['Heal'] = ['green']
    app.SPELLCOOLDOWNS['Heal'] = 2

def evaluateCommand(app):
    foundSpell = 'Spell not found'
    for spell in app.SPELLS:
        if(app.SPELLS[spell] == app.command):
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

    if(not spell in app.SPELLS):
        return

    if(app.spellCooldown > 0):
        return
    
    app.spell = spell
    app.spellCooldown = app.SPELLCOOLDOWNS[spell]
    app.startingSpellCooldown = app.spellCooldown

    if(spell == 'Dash'):
        player.dash()
    
    elif(spell == 'Fireball'):
        player.fireball(app)
    
    elif(spell == 'Freeze'):
        player.freeze(app)

    elif(spell == 'Heal'):
        player.heal(app)
        
