PLAYERSPRITES = {'idle':('wizard_idle', 2), 'forwards':('wizard_run_forwards', 4), 'backwards':('wizard_run_backwards', 4), 'left':('wizard_run_left', 4),
                 'right':('wizard_run_right', 4), 'cast':('wizard_cast', 2)}

def openAnimation(name, frames):
    L = []
    for frame in range(1, frames+1):
        L.append(f'{name}-{frame}')
    return L

