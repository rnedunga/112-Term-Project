import pyaudio
import numpy as np
from scipy.signal import find_peaks

def frequency_to_note(freq):
    A4 = 440.0  # Frequency of A4
    C0 = A4 * 2**(-4.75)  # Frequency of C0
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    if freq == 0:
        return "No note"
    h = round(12 * np.log2(freq / C0))
    octave = h // 12
    n = h % 12
    return note_names[n] + str(octave)

def evaluatePitch(app, noteList):
    
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
        noteList.pop(0)
        noteList.append(note)
    
    if(noteList[0] == noteList[1] == noteList[2]):
        app.noteDetected = True
        print(f"Detected note: {noteList[0]} (Frequency: {app.frequency} Hz)")
        return noteList[0]
    else:
        app.noteDetected = False

    return None

def evaluateColor(note):
    if(note == None):
        return None
    elif (note[:-1] == 'C' or note[:-1] == 'C#' or note[:-1] == 'F#' or note[:-1] == 'G'):
        return 'red'
    elif (note[:-1] == 'D' or note[:-1] == 'D#' or note[:-1] == 'G#' or note[:-1] == 'A'):
        return 'blue'
    elif (note[:-1] == 'E' or note[:-1] == 'F' or note[:-1] == 'A#' or note[:-1] == 'B'):
        return 'green'