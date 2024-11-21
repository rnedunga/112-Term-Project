spells = {'Dash':['blue'], 'Fireball':['red', 'green', 'red'], 'Thunder':['blue', 'red']}

def evaluateCommand(app):
    foundSpell = 'Spell not found'
    for spell in spells:
        if(spells[spell] == app.command):
            print(f"Cast {spell}")
            foundSpell = spell
            break

    app.commandTimer = 0

    return foundSpell

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