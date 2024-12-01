PLAYERSPRITES = {'idle':('wizard_idle', 2, 2), 'forwards':('wizard_run_forwards', 4, 5), 'backwards':('wizard_run_backwards', 4, 5), 'left':('wizard_run_left', 4, 5),
                 'right':('wizard_run_right', 4, 5), 'cast':('wizard_cast', 2, 5)}

ZOMBIESPRITES = {'idle':('zombie_idle', 2, 2), 'forwards':('zombie_run_forwards', 3, 5), 'backwards':('zombie_run_backwards', 2, 4), 'left':('zombie_run_left', 3, 5),
                 'right':('zombie_run_right', 3, 5)} # Credit: https://mesiiue.itch.io/simple-topdown-zombie

OBJECTSPRITES = {'bookshelf': 'bookshelf'}

EFFECTSPRITES = {'blood': 'blood'}

def openAnimation(name, frames):
    L = []
    for frame in range(1, frames+1):
        L.append(f'{name}-{frame}')
    return L

