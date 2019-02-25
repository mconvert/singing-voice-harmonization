from collections import Counter
import re


def _get_beat_intervals(beat_list):
    """ I: list of beat indices for on part
        O: list of beat intervals for one part
    """
    intervals = []
    lowest_b, highest_b = min(beat_list), max(beat_list)
    for beat_i in range(lowest_b, highest_b+1):
        indices = [j for j in range(len(beat_list)) if (beat_list[j] == beat_i)]
        intervals.append((min(indices), max(indices)))
    return intervals


def _find_most_common_label(beat_chords):
    c = Counter()
    for label in beat_chords:
        c[label] += 1
    most_common_c, count = c.most_common(1)[0]
    return most_common_c, count/len(beat_chords)



def _get_chord_separation_indices(ch_list):
    indices = []
    index_list = []
    for i in range(len(ch_list)):
        if (i == 0):
            indices.append(i)
        elif (i>0) and (i<len(ch_list)-1):
            if ch_list[i] == ch_list[i-1]:
                indices.append(i)
            else:
                index_list.append(indices)
                indices = [i]
        elif (i == len(ch_list)-1):
            if (ch_list[i] == ch_list[i-1]):
                indices.append(i)
                index_list.append(indices)
            else:
                index_list.append(indices)
                index_list.append([i])
                
    return index_list






def split_in_beats(part_chords, part_pitches, part_beats):
    """ I: chords 10msec samples for one song part
       pitch (f0 or MIDI) 10msec samples for one song part
       beat indices at every 10msec for one song part
    O: list of list of pitch sequences per beat
       list of chord label per beat
    """
    chords_by_beat = []
    pitch_seqs_by_beat = []
    intervals = _get_beat_intervals(part_beats)
    for (start, end) in intervals:
        pitch_seq = part_pitches[start:end+1]
        most_common_c, presence = _find_most_common_label(part_chords[start:end+1])
        pitch_seqs_by_beat.append(pitch_seq)
        chords_by_beat.append(most_common_c)

    return pitch_seqs_by_beat, chords_by_beat



def truncate_chord_to_triad_rwc(label):
    """ I: chord label (from RWC dataset notation)
        O: chord label truncated to triad
    """
    pattern = "^([NA-G][#b]?:?(?:[minmajdimaugsushdim]{3,4})?)" #triad only
    m = re.match(pattern, label)
    
    trunc_lab = m.group(1)
    # Convert seventh labels to triad
    if "hdim" in trunc_lab:
        trunc_lab = trunc_lab[:-4] + "dim"
    elif trunc_lab[-1] == ':':
        trunc_lab = trunc_lab + "maj"
        
    # Convert flats to sharps
    if "Ab" in trunc_lab:
        trunc_lab = "G#" + trunc_lab[2:]
    elif "Bb" in trunc_lab:
        trunc_lab = "A#" + trunc_lab[2:]
    elif "Cb" in trunc_lab:
        trunc_lab = "B" + trunc_lab[2:]
    elif "Db" in trunc_lab:
        trunc_lab = "C#" + trunc_lab[2:]
    elif "Eb" in trunc_lab:
        trunc_lab = "D#" + trunc_lab[2:]
    elif "Fb" in trunc_lab:
        trunc_lab = "E" + trunc_lab[2:]
    elif "Gb" in trunc_lab:
        trunc_lab = "F#" + trunc_lab[2:]
    return trunc_lab


