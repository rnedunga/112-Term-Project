#THIS WHOLE FILE IS WRITTEN BY TA
#THIS IS NOT MY FILE
#IT WASNT WRITTEN BY ME
#IT WAS IN AN ED POST
#NOT ME WHO WROTE THIS

from cmu_graphics import Sound
import os, pathlib
def loadSound(relativePath):
    # Convert to absolute path (because pathlib.Path only takes absolute paths)
    absolutePath = os.path.abspath(relativePath)
    # Get local file URL
    url = pathlib.Path(absolutePath).as_uri()
    # Load Sound file from local URL
    return Sound(url)